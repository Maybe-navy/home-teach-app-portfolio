from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.core import signing  # 生徒検索用の一時トークン生成に使用
from django.core.signing import BadSignature, SignatureExpired
from django.urls import reverse
from personal_info.models import (
    ClassSchedule,
    MaterialUsage,
    TeacherProfile,
    ClassKarte,
    StudentProfile,
    Subject,
    TeacherStudentAssignment,
    TeachingMaterial,
)
from personal_info.forms import MaterialList
from .forms import ClassKarteForm, TeacherScheduleEditForm
from datetime import date
import logging
from django.utils.dateparse import parse_date
from django.db.models import Q
from django.core.paginator import Paginator

import io
from django.http import HttpResponse
from personal_info.utils import has_conflict
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from django.conf import settings
from pathlib import Path
from . import pdf_utils
from .permissions import is_teacher


def _is_teacher(user) -> bool:
    if not is_teacher(user):
        raise PermissionDenied("権限がありません。")
    return True

# Django 5+ では django.utils.encoding に BOM_UTF8 が存在しないため自前定義
BOM_UTF8 = "\ufeff"

_STUDENT_SEARCH_SALT = "teacher-portal-student-access"
_STUDENT_SEARCH_MAX_AGE = 300  # 有効期限は 5 分


def _build_student_search_token(user_id: int, student_id: int) -> str:
    signer = signing.TimestampSigner(salt=_STUDENT_SEARCH_SALT)
    return signer.sign(f"{user_id}:{student_id}")


def _has_student_search_access(request, student_id: int) -> bool:
    token = request.GET.get("access")
    if not token or not request.user.is_authenticated:
        return False
    signer = signing.TimestampSigner(salt=_STUDENT_SEARCH_SALT)
    try:
        payload = signer.unsign(token, max_age=_STUDENT_SEARCH_MAX_AGE)
        uid_str, sid_str = payload.split(":", 1)
        return int(uid_str) == request.user.id and int(sid_str) == student_id
    except (BadSignature, SignatureExpired, ValueError):
        return False


def _register_jp_font():
    try:
        font_path = Path(settings.BASE_DIR) / "static" / "fonts" / "NotoSansJP-Regular.otf"
        if not font_path.exists():
            font_path = Path(settings.BASE_DIR) / "static" / "fonts" / "NotoSansJP-Regular.ttf"
        if font_path.exists():
            pdfmetrics.registerFont(TTFont("JP", str(font_path)))
            return "JP"
    except Exception:
        pass
    return "Helvetica"


def _student_schedule_qs(student, params):
    qs = (
        ClassSchedule.objects
        .filter(student=student)
        .select_related("teacher", "student", "subject")
        .order_by("class_date", "start_time", "id")
    )

    df = params.get("date_from") or ""
    dt = params.get("date_to") or ""
    subject_id = params.get("subject") or ""
    teacher_id = params.get("teacher") or ""
    q = (params.get("q") or "").strip()

    if df:
        d = parse_date(df)
        if d:
            qs = qs.filter(class_date__gte=d)
    if dt:
        d = parse_date(dt)
        if d:
            qs = qs.filter(class_date__lte=d)
    if subject_id:
        qs = qs.filter(subject_id=subject_id)
    if teacher_id:
        qs = qs.filter(teacher_id=teacher_id)
    if q:
        qs = qs.filter(
            Q(student__name__icontains=q)
            | Q(teacher__name__icontains=q)
            | Q(subject__name__icontains=q)
        )
    return qs

@login_required
@user_passes_test(_is_teacher, login_url=None)
def teacher_dashboard(request):
    """講師用ダッシュボード：直近の授業を1件だけ渡す"""
    teacher = get_object_or_404(TeacherProfile, user=request.user)
    next_schedule = (
        ClassSchedule.objects
        .filter(teacher=teacher, class_date__gte=date.today())
        .order_by('class_date', 'start_time')
        .first()
    )
    return render(request, 'teacher_portal/teacher_dashboard.html', {
        'next_schedule': next_schedule,
        'is_teacher': True,
    })

# カルテ編集（講師専用）
@login_required
@user_passes_test(_is_teacher, login_url=None)
def edit_karte_view(request, schedule_id):
    # ログイン講師のプロフィール
    teacher_profile = get_object_or_404(TeacherProfile, user=request.user)

    # 自分の授業のみ編集可
    schedule = get_object_or_404(
        ClassSchedule.objects.select_related('student', 'subject'),
        id=schedule_id, teacher=teacher_profile
    )

    # カルテ用意（なければ作成）
    karte, _created = ClassKarte.objects.get_or_create(
        schedule=schedule,
        defaults={
            "class_date": schedule.class_date,
            "student": schedule.student,
            "teacher": schedule.teacher,
            "subject": schedule.subject,
        }
    )

    if karte.is_confirmed:
        return HttpResponseForbidden("確定済みのため講師側からは編集できません。")

    if request.method == "POST":
        is_draft = ('save_draft' in request.POST)
        form = ClassKarteForm(request.POST, instance=karte)

        # 下書き時は必須を緩める（未入力でも通す）
        if is_draft:
            for f in ("karte_summary", "karte_detail", "material"):
                if f in form.fields:
                    form.fields[f].required = False

        if form.is_valid():
            instance = form.save(commit=False)

            # 画面に出していない固定項目を「必ず」上書き
            instance.schedule = schedule
            instance.class_date = schedule.class_date
            instance.student = schedule.student
            instance.teacher = schedule.teacher
            instance.subject = schedule.subject

            # status を使っている場合のみ設定（無ければ無視）
            if hasattr(instance, "status"):
                if is_draft and hasattr(ClassKarte, "STATUS_DRAFT"):
                    instance.status = ClassKarte.STATUS_DRAFT
                elif (not is_draft) and hasattr(ClassKarte, "STATUS_SUBMITTED"):
                    instance.status = ClassKarte.STATUS_SUBMITTED

            instance.save()

            # 「提出」時は最終確定として扱い、授業を実施済みにする
            if not is_draft:
                instance.confirm(by=teacher_profile)

            # 使用教材履歴（選択されていれば）
            if instance.material and instance.student:
                MaterialUsage.objects.get_or_create(student=instance.student, material=instance.material)

            if is_draft:
                messages.success(request, "カルテを下書き保存しました。")
            else:
                messages.success(request, "カルテを提出し、実績を確定しました。")
            return redirect("teacher_portal:schedule_board")
        else:
            messages.error(request, "入力内容に不備があります。赤字のエラーをご確認ください。")
    else:
        form = ClassKarteForm(instance=karte)

    # ※ テンプレ名は実ファイルに合わせる（本ZIPは edit_karte.html でした）
    return render(request, "teacher_portal/edit_karte.html", {
        "form": form,
        "schedule": schedule,
        "karte": karte,
        "is_teacher": True,
    })


@login_required
@user_passes_test(_is_teacher, login_url=None)
def karte_confirm_confirm_view(request, schedule_id: int):
    sc = get_object_or_404(ClassSchedule, pk=schedule_id)
    karte, _ = ClassKarte.objects.get_or_create(schedule=sc)
    if karte.is_confirmed:
        return HttpResponseForbidden("このカルテは確定済みです。")

    if request.method == "POST":
        tp = get_object_or_404(TeacherProfile, user=request.user)
        karte.confirm(by=tp)
        return redirect("teacher_portal:teacher_dashboard")

    return render(
        request,
        "teacher_portal/karte_confirm_confirm.html",
        {"schedule": sc, "karte": karte},
    )

@login_required
@user_passes_test(_is_teacher, login_url=None)
def karte_pdf(request, schedule_id):
    teacher_profile = get_object_or_404(TeacherProfile, user=request.user)
    schedule = get_object_or_404(
        ClassSchedule.objects.select_related('student', 'subject'),
        id=schedule_id, teacher=teacher_profile
    )
    karte, _ = ClassKarte.objects.get_or_create(
        schedule=schedule,
        defaults={
            "class_date": schedule.class_date,
            "student": schedule.student,
            "teacher": schedule.teacher,
            "subject": schedule.subject,
        }
    )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    font_name = pdf_utils.get_font_name()
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="JPTitle", fontName=font_name, fontSize=16, leading=20, spaceAfter=12))
    styles.add(ParagraphStyle(name="JPText", fontName=font_name, fontSize=10, leading=14, spaceAfter=6))

    def ev_label(v):
        return {"more":"もう少し","good":"よくできました","great":"大変よくできました"}.get(v, "-")

    story = []
    story.append(Paragraph("授業カルテ", styles["JPTitle"]))

    meta_tbl = Table([
        ["授業日", str(karte.class_date or schedule.class_date)],
        ["講師", schedule.teacher.name],
        ["生徒", schedule.student.name],
        ["科目", str(schedule.subject or "-")],
    ], colWidths=[80, 400])
    meta_tbl.setStyle(TableStyle([
        ("FONTNAME", (0,0), (-1,-1), font_name),
        ("FONTSIZE", (0,0), (-1,-1), 10),
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("BACKGROUND", (0,0), (0,-1), colors.HexColor("#f7f7f7")),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(meta_tbl)
    story.append(Spacer(1, 8))

    story.append(Paragraph(f"遅刻の有無: {'あり' if karte.tardy else 'なし'}", styles["JPText"]))
    story.append(Paragraph(f"評価: {ev_label(karte.evaluation)}", styles["JPText"]))
    story.append(Paragraph(f"使用教材: {getattr(karte.material, 'title', '-')}", styles["JPText"]))
    if karte.material_pages:
        story.append(Paragraph(f"ページ: {karte.material_pages}", styles["JPText"]))
    if karte.goal:
        story.append(Paragraph(f"目標: {karte.goal}", styles["JPText"]))

    story.append(Spacer(1, 6))
    story.append(Paragraph("授業概要", styles["JPText"]))
    story.append(Paragraph(karte.karte_summary or "-", styles["JPText"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph("授業詳細", styles["JPText"]))
    story.append(Paragraph(karte.karte_detail or "-", styles["JPText"]))

    doc.build(story)
    pdf = buf.getvalue()
    buf.close()

    filename = f"karte_{schedule.id}.pdf"
    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename={filename}'

    from personal_info.models import DownloadLog

    DownloadLog.objects.create(
        user=request.user if request.user.is_authenticated else None,
        student=schedule.student,
        kind="karte_pdf",
        count=1,
    )
    return resp

@login_required
@user_passes_test(_is_teacher, login_url=None)
def karte_view(request, schedule_id):
    """講師向け: カルテの閲覧専用画面（確定後の参照用）。"""
    teacher_profile = get_object_or_404(TeacherProfile, user=request.user)
    schedule = get_object_or_404(
        ClassSchedule.objects.select_related('student', 'subject'),
        id=schedule_id, teacher=teacher_profile
    )
    karte, _ = ClassKarte.objects.get_or_create(
        schedule=schedule,
        defaults={
            "class_date": schedule.class_date,
            "student": schedule.student,
            "teacher": schedule.teacher,
            "subject": schedule.subject,
        }
    )
    return render(
        request,
        'teacher_portal/karte_detail.html',
        {"schedule": schedule, "karte": karte, "is_teacher": True},
    )

@login_required
@user_passes_test(_is_teacher, login_url=None)
def create_material_view(request):
    next_url = request.POST.get("next") or request.GET.get("next", "")
    if request.method == 'POST':
        form = MaterialList(request.POST)
        form.fields['subject'].required = True
        if form.is_valid():
            material = form.save(commit=False)
            material.created_by = request.user
            material.save()
            messages.success(request, "教材を登録しました。")
            redirect_to = next_url or 'teacher_portal:schedule_board'
            return redirect(redirect_to)
        messages.error(request, "入力内容に不備があります。赤字のエラーをご確認ください。")
    else:
        form = MaterialList()
        form.fields['subject'].required = True
    return render(
        request,
        'materials/material_create.html',
        {
            'form': form,
            'next': next_url,
            'is_teacher': True,
            'default_back_url': reverse('teacher_portal:schedule_board'),
            'page_title': '教材を新規登録',
            'submit_label': '登録',
            'form_description': '授業で使用する教材の情報を登録します。',
        },
    )


@login_required
@user_passes_test(_is_teacher, login_url=None)
def edit_material_view(request, material_id: int):
    material = get_object_or_404(TeachingMaterial, pk=material_id)
    next_url = request.POST.get("next") or request.GET.get("next", "")

    if request.method == 'POST':
        form = MaterialList(request.POST, instance=material)
        form.fields['subject'].required = True
        if form.is_valid():
            form.save()
            messages.success(request, "教材情報を更新しました。")
            redirect_to = next_url or 'teacher_portal:schedule_board'
            return redirect(redirect_to)
        messages.error(request, "入力内容に不備があります。赤字のエラーをご確認ください。")
    else:
        form = MaterialList(instance=material)
        form.fields['subject'].required = True

    return render(
        request,
        'materials/material_create.html',
        {
            'form': form,
            'next': next_url,
            'is_teacher': True,
            'default_back_url': reverse('teacher_portal:schedule_board'),
            'page_title': '教材情報を編集',
            'submit_label': '更新',
            'form_description': f'{material.title} の情報を編集します。',
        },
    )

# 講師の担当授業確認（検索つき）
@login_required
@user_passes_test(_is_teacher, login_url=None)
def schedule_board_view(request):
    teacher_profile = get_object_or_404(TeacherProfile, user=request.user)
    assigned_student_ids = set(
        TeacherStudentAssignment.objects.filter(teacher=teacher_profile)
        .values_list("student_id", flat=True)
    )

    q = (request.GET.get("q") or "").strip()
    base = (
        ClassSchedule.objects
        .select_related("student", "subject", "teacher")
        .filter(Q(teacher=teacher_profile) | Q(student_id__in=assigned_student_ids))
        .order_by("-class_date", "-start_time", "-id")
    )
    if q:
        base = base.filter(
            Q(student__name__icontains=q) |
            Q(subject__name__icontains=q)
        )

    try:
        from teacher_portal.permissions import can_teacher_view_student
    except ImportError:
        can_teacher_view_student = None

    student_search_results = []
    if q:
        matches = (
            StudentProfile.objects.filter(name__icontains=q)
            .order_by("name")
            .only("id", "name")
        )[:10]
        for student in matches:
            if can_teacher_view_student:
                direct_access = can_teacher_view_student(request.user, student)
            else:
                direct_access = student.id in assigned_student_ids
            token = None
            if not direct_access:
                token = _build_student_search_token(request.user.id, student.id)
            student_search_results.append(
                {
                    "student": student,
                    "access_token": token,
                    "is_assigned": direct_access,
                }
            )

    pending_qs = base.filter(status="pending")
    scheduled_qs = base.filter(status="scheduled")
    done_qs = base.filter(status="done")

    p1 = Paginator(pending_qs, 10).get_page(request.GET.get("p1"))
    p2 = Paginator(scheduled_qs, 10).get_page(request.GET.get("p2"))
    p3 = Paginator(done_qs, 10).get_page(request.GET.get("p3"))

    return render(
        request,
        "teacher_portal/schedule_board.html",
        {
            "q": q,
            "p1": p1,
            "p2": p2,
            "p3": p3,
            "is_teacher": True,
            "teacher_profile": teacher_profile,
            "assigned_student_ids": assigned_student_ids,
            "student_search_results": student_search_results,
        },
    )

@login_required
@user_passes_test(_is_teacher, login_url=None)
def teacher_edit_schedule_view(request, schedule_id):
    teacher_profile = get_object_or_404(TeacherProfile, user=request.user)
    schedule = get_object_or_404(ClassSchedule, id=schedule_id)

    if schedule.teacher_id != teacher_profile.id:
        if not TeacherStudentAssignment.objects.filter(
            teacher=teacher_profile, student=schedule.student
        ).exists():
            raise PermissionDenied("権限がありません。担当外の授業です。")

    if schedule.status == ClassSchedule.STATUS_DONE:
        return HttpResponseForbidden("実施済のため変更できません。")

    allow_datetime_edit = (schedule.status != ClassSchedule.STATUS_DONE)

    if request.method == "POST":
        data = request.POST.copy()
        if not allow_datetime_edit:
            # 改ざん防止：確定後は日時を固定
            data["class_date"] = schedule.class_date
            data["start_time"] = schedule.start_time
            data["end_time"] = schedule.end_time
        form = TeacherScheduleEditForm(data, instance=schedule)
        if form.is_valid():
            cd = form.cleaned_data
            teacher_id = cd["teacher"].id if cd.get("teacher") else None
            if has_conflict(
                cd["class_date"],
                cd["start_time"],
                cd["end_time"],
                teacher_id,
                schedule.student_id,
                exclude_id=schedule.id,
            ):
                messages.error(
                    request,
                    "同一時間帯に既存の予定があり、重複しています。（教師または生徒のどちらかが重複）",
                )
                return render(
                    request,
                    "teacher_portal/schedule_edit.html",
                    {
                        "form": form,
                        "schedule": schedule,
                        "allow_datetime_edit": allow_datetime_edit,
                        "is_teacher": True,
                    },
                    status=400,
                )
            schedule = form.save(commit=False)
            schedule.is_absent = bool(request.POST.get("is_absent"))
            schedule.is_tardy = bool(request.POST.get("is_tardy"))
            schedule.note = request.POST.get("note", "")
            schedule.save()
            msg = "授業を更新しました。"
            if not allow_datetime_edit:
                msg += "（確定済みのため日時は変更できません）"
            messages.success(request, msg)
            return redirect("teacher_portal:schedule_board")
    else:
        form = TeacherScheduleEditForm(instance=schedule)
        if not allow_datetime_edit:
            # UI上も分かるように disable
            for f in ("class_date", "start_time", "end_time"):
                if f in form.fields:
                    form.fields[f].widget.attrs["disabled"] = True

    return render(request, "teacher_portal/schedule_edit.html", {
        "form": form,
        "schedule": schedule,
        "allow_datetime_edit": allow_datetime_edit,
        "is_teacher": True,
    })

@login_required
@user_passes_test(_is_teacher, login_url=None)
def student_schedule_list_view(request, student_id: int):
    student = get_object_or_404(StudentProfile, pk=student_id)
    try:
        from teacher_portal.permissions import can_teacher_view_student
    except ImportError:
        can_teacher_view_student = None
    has_search_access = _has_student_search_access(request, student.id)

    if can_teacher_view_student:
        has_direct_access = can_teacher_view_student(request.user, student)
    else:
        has_direct_access = TeacherStudentAssignment.objects.filter(
            teacher__user=request.user,
            student=student,
        ).exists()

    if not has_direct_access and not has_search_access:
        raise PermissionDenied("権限がありません。割当外の生徒です。")

    qs = _student_schedule_qs(student, request.GET)
    subjects = Subject.objects.only("id", "name").order_by("name")
    teachers = TeacherProfile.objects.only("id", "name").order_by("name")

    return render(request, "teacher_portal/student_schedule_list.html", {
        "student": student,
        "schedules": qs,
        "subjects": subjects,
        "teachers": teachers,
        "date_from": request.GET.get("date_from", ""),
        "date_to": request.GET.get("date_to", ""),
        "subject_id": request.GET.get("subject", ""),
        "teacher_id": request.GET.get("teacher", ""),
        "q": request.GET.get("q", ""),
        "is_teacher": True,
        "viewing_via_search": has_search_access and not has_direct_access,
    })

@login_required
@user_passes_test(_is_teacher, login_url=None)
def student_schedule_pdf_view(request, student_id: int):
    student = get_object_or_404(StudentProfile, pk=student_id)
    try:
        from teacher_portal.permissions import can_teacher_view_student
    except ImportError:
        can_teacher_view_student = None
    has_search_access = _has_student_search_access(request, student.id)

    if can_teacher_view_student:
        has_direct_access = can_teacher_view_student(request.user, student)
    else:
        has_direct_access = TeacherStudentAssignment.objects.filter(
            teacher__user=request.user,
            student=student,
        ).exists()

    if not has_direct_access and not has_search_access:
        raise PermissionDenied("権限がありません。割当外の生徒です。")

    qs = _student_schedule_qs(student, request.GET)

    df = request.GET.get("date_from")
    dt = request.GET.get("date_to")

    try:
        response = HttpResponse(content_type="application/pdf")
        filename = f"student_{student_id}_schedules.pdf"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        p = canvas.Canvas(response, pagesize=A4)
        width, height = A4
        left = 15 * mm
        right = width - 15 * mm
        bottom = 15 * mm
        line_h = 7 * mm

        font_name = pdf_utils.get_font_name()
        meta_lines = [f"生徒: {getattr(student, 'name', '-')}"]
        if df or dt:
            meta_lines.append(
                f"期間: {df or '（指定なし）'} 〜 {dt or '（指定なし）'}"
            )
        y = pdf_utils.draw_header(p, "生徒の授業予定一覧", meta_lines, font_name)
        cols = [
            ("予定日", 20 * mm),
            ("開始", 15 * mm),
            ("終了", 15 * mm),
            ("講師名", 30 * mm),
            ("科目名", 25 * mm),
            ("実施", 10 * mm),
            ("欠席", 10 * mm),
            ("遅刻", 10 * mm),
            ("備考", right - left - (20 + 15 + 15 + 30 + 25 + 10 + 10 + 10) * mm),
        ]
        rows = [
            [
                sc.class_date.strftime("%Y-%m-%d"),
                sc.start_time.strftime("%H:%M"),
                sc.end_time.strftime("%H:%M"),
                getattr(sc.teacher, "name", "-") or "-",
                getattr(sc.subject, "name", "-") if sc.subject else "-",
                "○" if sc.is_held else "",
                "○" if sc.is_absent else "",
                "○" if sc.is_tardy else "",
                sc.note or "",
            ]
            for sc in qs
        ]
        pdf_utils.draw_table(p, left, y, cols, rows, font_name, 10, line_h, right, bottom)
        p.showPage()
        p.save()
    except Exception:
        # 予期せぬエラー内容を監視できるようログに残し、利用者には共通メッセージを返す。
        logger = logging.getLogger(__name__)
        logger.exception(
            "PDF generation failed",
            extra={"student_id": student_id, "user_id": request.user.id},
        )
        return HttpResponse(
            "PDF生成に失敗しました。時間をおいて再度お試しください。",
            status=500,
        )

    from personal_info.models import DownloadLog

    DownloadLog.objects.create(
        user=request.user if request.user.is_authenticated else None,
        student=student,
        kind="student_schedules_pdf",
        count=qs.count(),
    )
    return response


@login_required
@user_passes_test(_is_teacher, login_url=None)
def student_schedule_csv_view(request, student_id: int):
    import csv
    student = get_object_or_404(StudentProfile, pk=student_id)
    try:
        from teacher_portal.permissions import can_teacher_view_student
    except ImportError:
        can_teacher_view_student = None
    has_search_access = _has_student_search_access(request, student.id)

    if can_teacher_view_student:
        has_direct_access = can_teacher_view_student(request.user, student)
    else:
        has_direct_access = TeacherStudentAssignment.objects.filter(
            teacher__user=request.user,
            student=student,
        ).exists()

    if not has_direct_access and not has_search_access:
        raise PermissionDenied("権限がありません。割当外の生徒です。")

    qs = _student_schedule_qs(student, request.GET)
    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="{student.id}_schedules.csv"'
    resp.write("\ufeff")
    w = csv.writer(resp)
    w.writerow(["予定日", "開始", "終了", "講師名", "科目名"])
    for sc in qs:
        w.writerow([
            sc.class_date,
            sc.start_time,
            sc.end_time,
            getattr(sc.teacher, "name", "-"),
            getattr(sc.subject, "name", "-"),
        ])
    return resp
