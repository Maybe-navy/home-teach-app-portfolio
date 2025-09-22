"""管理者ポータルで利用するビュー群。"""

import csv, io
from types import SimpleNamespace

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Sum, Count, F, Q
from django.db import transaction
from django.contrib.auth.models import User
from django.utils.crypto import get_random_string
from django.http import HttpResponse, HttpResponseForbidden
from django.urls import reverse
import os
import secrets, string
import sys
from django.core.signing import dumps, loads, BadSignature, SignatureExpired
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator
from django.conf import settings
from pathlib import Path

from datetime import date
from collections import defaultdict

from .forms import (
    TeacherRegistForm,
    StudentRegistForm,
    RewardCategoryForm,
    StudentRewardForm,
    RewardCategoryCreateForm,
    BillingCategoryForm,
    BillingCategoryCreateForm,
    AccountStatusSearchForm,
    TeacherEditForm,
    StudentEditForm,
    CSVUploadForm,
    AssignmentCreateForm,
)

from personal_info.models import (
    TeacherProfile,
    StudentProfile,
    ClassSchedule,
    Subject,
    RewardCategory,
    BillingCategory,
    AdminProfile,
    RewardClosing,
    RewardClosingTeacher,
    TeacherStudentAssignment,
    ClassKarte,
    TeachingMaterial,
)
from personal_info.forms import SubjectForm, MaterialList
from .forms import ClassScheduleForm
from personal_info.utils import (
    closing_range,
    parse_ym,
    get_student_billing,
    get_teacher_reward,
    has_conflict,
)

from core.utils import generate_compliant_password, cached_count
from core.models import UserProfile, AccessLog
from core.demo_signals import demo_delete_override

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def _add_month(y: int, m: int, delta: int):
    """(y,m) に delta ヶ月を加減して (Y,M) を返す（python-dateutil なしで安全）"""
    t = y * 12 + (m - 1) + delta
    return t // 12, t % 12 + 1

def _register_jp_font():
    """NotoSansJP を登録。見つからなければ Helvetica を使う。"""
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


def _demo_lockdown_active() -> bool:
    if getattr(settings, "DEMO_READ_ONLY_BYPASS", False):
        return False
    if os.environ.get("PYTEST_CURRENT_TEST") or "pytest" in sys.modules:
        return False
    return bool(getattr(settings, "DEMO_READ_ONLY", False))


def _demo_staff_sensitive_forbidden(request):
    if not _demo_lockdown_active():
        return None
    user = getattr(request, "user", None)
    if getattr(user, "is_staff", False):
        return None
    if getattr(user, "is_authenticated", False):
        profile = getattr(user, "userprofile", None)
        if getattr(profile, "user_type", None) == "admin":
            return None
    return HttpResponseForbidden("Demo モードでは操作できません。")

@login_required
def admin_dashboard(request):
    if not is_admin(request.user):
        return HttpResponseForbidden("権限がありません")
    return render(request, 'admin_portal/admin_dashboard.html')


def teacher_register(request):
    if request.method == "POST":
        form = TeacherRegistForm(request.POST)
        if form.is_valid():
            user, password = form.save()

            try:
                teacher = TeacherProfile.objects.get(user=user)
            except TeacherProfile.DoesNotExist:
                teacher = None

            return render(request, 'admin_portal/teachers/teacher_confirm.html',{
                'user': user,
                'password': password,
                'teacher': teacher,
            })
    else:
        form = TeacherRegistForm()
    return render(request, 'admin_portal/teachers/teacher_register.html', {'form': form})

def student_register(request):
    if request.method == "POST":
        form = StudentRegistForm(request.POST)
        if form.is_valid():
            user, password = form.save()

            try:
                student = StudentProfile.objects.get(user=user)
            except StudentProfile.DoesNotExist:
                student = None

            return render(request, 'admin_portal/students/student_confirm.html',{
                'user': user,
                'password': password,
                'student': student,
            })
    else:
        form = StudentRegistForm()
    return render(request, 'admin_portal/students/student_register.html', {'form': form})

def is_admin(user):
    """ログイン済みユーザーが管理者アカウントか判定する。"""
    return user.is_authenticated and hasattr(user, 'userprofile') and user.userprofile.user_type == 'admin'


@login_required
@user_passes_test(is_admin, login_url=None)
def material_create_view(request):
    """管理者向け: 教材情報を新規登録する。"""

    next_url = request.POST.get("next") or request.GET.get("next", "")

    if request.method == "POST":
        form = MaterialList(request.POST)
        form.fields["subject"].required = True
        if form.is_valid():
            material = form.save(commit=False)
            material.created_by = request.user
            material.save()

            redirect_to = next_url
            messages.success(request, "教材を登録しました。")
            if redirect_to:
                return redirect(redirect_to)
            return redirect("personal_info:material_list")

        messages.error(request, "入力内容に不備があります。赤字のエラーをご確認ください。")
    else:
        form = MaterialList()
        form.fields["subject"].required = True

    return render(
        request,
        "materials/material_create.html",
        {
            "form": form,
            "next": next_url,
            "default_back_url": reverse("personal_info:material_list"),
            "page_title": "教材を新規登録",
            "submit_label": "登録",
            "form_description": "授業で使用する教材の情報を登録します。",
        },
    )


@login_required
@user_passes_test(is_admin, login_url=None)
def material_edit_view(request, material_id: int):
    """管理者向け: 既存の教材情報を更新する。"""

    material = get_object_or_404(TeachingMaterial, pk=material_id)
    next_url = request.POST.get("next") or request.GET.get("next", "")

    if request.method == "POST":
        form = MaterialList(request.POST, instance=material)
        form.fields["subject"].required = True
        if form.is_valid():
            form.save()
            messages.success(request, "教材情報を更新しました。")
            if next_url:
                return redirect(next_url)
            return redirect("personal_info:material_list")
        messages.error(request, "入力内容に不備があります。赤字のエラーをご確認ください。")
    else:
        form = MaterialList(instance=material)
        form.fields["subject"].required = True

    return render(
        request,
        "materials/material_create.html",
        {
            "form": form,
            "next": next_url,
            "default_back_url": reverse("personal_info:material_list"),
            "page_title": "教材情報を編集",
            "submit_label": "更新",
            "form_description": f"{material.title} の情報を編集します。",
        },
    )


@login_required
def delete_schedule_view(request, schedule_id):
    if not is_admin(request.user):
        return HttpResponseForbidden("権限がありません")

    schedule = get_object_or_404(ClassSchedule, id=schedule_id)

    if request.method == 'POST':
        schedule.delete()
        messages.success(request, "該当授業を削除しました。")
        return redirect('admin_portal:schedule_board')

    return render(request, 'admin_portal/schedules/delete_schedule.html', {'schedule':schedule})

@login_required
def edit_subject(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    if request.method == 'POST':
        form = SubjectForm(request.POST, instance=subject)
        if form.is_valid():
            form.save()
            return redirect('personal_info:subject_list')
    else:
        form = SubjectForm(instance=subject)
    return render(request, 'admin_portal/edit_subject.html', {'form':form, 'subject':subject})

@login_required
@user_passes_test(is_admin)
def delete_subject(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    subject.delete()
    return redirect('personal_info:subject_list')

@login_required
@user_passes_test(is_admin)
def reset_user_password(request, user_id):
    forbidden = _demo_staff_sensitive_forbidden(request)
    if forbidden:
        return forbidden
    user = get_object_or_404(User, id=user_id)

    new_password = generate_compliant_password(length=12)  # ランダムな仮パスワードを再発行
    user.set_password(new_password)
    user.save()

    profile = getattr(user, 'userprofile', None)
    if profile:
        profile.is_temporary_password = True
        profile.save()

    return render(request, 'admin_portal/accounts/reset_password.html', {
        'user': user,
        'password': new_password,
    })

@login_required
@user_passes_test(lambda u: u.is_authenticated and hasattr(u, 'userprofile') and u.userprofile.user_type == 'admin')
def reward_report_view(request):
    """
    締日25日ベースで選択月(ym=YYYY-MM)を集計。
    ・実績ゼロでも講師/生徒ごとに 0 行を出す
    ・status / is_confirmed のどちらにも寛容に対応
    ・CSV出力は ?ym=YYYY-MM&export=csv
    """

    """HTML 版（既存）。月指定+0安全はそのまま流用."""
    ym = request.GET.get("ym")
    today = date.today()
    parsed = parse_ym(ym) if ym else None
    year, month = parsed if parsed else (today.year, today.month)
    start_date, end_date = closing_range(year, month)

    py, pm = _add_month(year, month, -1)
    ny, nm = _add_month(year, month, +1)
    ym_str     = f"{year:04d}-{month:02d}"
    prev_ymstr = f"{py:04d}-{pm:02d}"
    next_ymstr = f"{ny:04d}-{nm:02d}"

    qs = (
        ClassSchedule.objects
        .filter(class_date__range=[start_date, end_date], karte__is_confirmed=True)
        .select_related("teacher", "student")
    )

    def teacher_rows():
        rows = []
        for t in TeacherProfile.objects.all().order_by("name"):
            t_qs = [s for s in qs if s.teacher_id == t.id]
            classes = len(t_qs)
            total = 0
            for s in t_qs:
                try:
                    per = get_teacher_reward(s.student) or 0
                except Exception:
                    per = (
                        getattr(getattr(s.student, 'reward_category', None), 'reward_per_class', None)
                        or getattr(s.student, 'custom_reward_per_class', None)
                        or 0
                    )
                total += int(per or 0)
            rows.append(SimpleNamespace(teacher=t, classes=int(classes or 0), total_reward=int(total or 0)))
        return rows

    def student_rows():
        rows = []
        for st in StudentProfile.objects.all().order_by("name"):
            s_qs = [s for s in qs if s.student_id == st.id]
            classes = len(s_qs)
            total = 0
            for s in s_qs:
                try:
                    per = get_student_billing(s.student) or 0
                except Exception:
                    per = getattr(s.student, 'billing_per_class', None) or 0
                total += int(per or 0)
            rows.append(SimpleNamespace(student=st, classes=int(classes or 0), total_fee=int(total or 0)))
        return rows

    t_rows = teacher_rows()
    s_rows = student_rows()

    if request.GET.get("export") == "csv":
        resp = HttpResponse(content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = f'attachment; filename=reward_{ym_str}.csv'
        w = csv.writer(resp)
        w.writerow(["期間", f"{start_date}〜{end_date}"])
        w.writerow([])
        w.writerow(["講師名", "コマ数", "合計報酬"])
        for r in t_rows:
            w.writerow([r.teacher.name, r.classes, r.total_reward])
        w.writerow([])
        w.writerow(["生徒名", "コマ数", "合計請求額"])
        for r in s_rows:
            w.writerow([r.student.name, r.classes, r.total_fee])
        return resp

    return render(request, "admin_portal/rewards/reward_report.html", {
        "ym": ym_str, "prev_ym": prev_ymstr, "next_ym": next_ymstr,
        "start_date": start_date, "end_date": end_date,
        "teacher_rows": t_rows, "student_rows": s_rows,
    })


@login_required
@user_passes_test(lambda u: u.is_authenticated and hasattr(u, 'userprofile') and u.userprofile.user_type == 'admin')
def reward_report_pdf(request):
    """PDF ダウンロード版（ReportLab）"""
    ym = request.GET.get("ym")
    today = date.today()
    parsed = parse_ym(ym) if ym else None
    year, month = parsed if parsed else (today.year, today.month)
    start_date, end_date = closing_range(year, month)
    ym_str = f"{year:04d}-{month:02d}"

    # HTML 版と同じ集計（重複を避けるなら共通関数化してOK）
    qs = (
        ClassSchedule.objects
        .filter(class_date__range=[start_date, end_date], karte__is_confirmed=True)
        .select_related("teacher", "student")
    )

    def teacher_rows():
        rows = []
        for t in TeacherProfile.objects.all().order_by("name"):
            t_qs = [s for s in qs if s.teacher_id == t.id]
            classes = len(t_qs)
            total = 0
            for s in t_qs:
                try:
                    per = get_teacher_reward(s.student) or 0
                except Exception:
                    per = (
                        getattr(getattr(s.student, 'reward_category', None), 'reward_per_class', None)
                        or getattr(s.student, 'custom_reward_per_class', None)
                        or 0
                    )
                total += int(per or 0)
            rows.append((t.name, classes, total))
        return rows

    def student_rows():
        rows = []
        for st in StudentProfile.objects.all().order_by("name"):
            s_qs = [s for s in qs if s.student_id == st.id]
            classes = len(s_qs)
            total = 0
            for s in s_qs:
                try:
                    per = get_student_billing(s.student) or 0
                except Exception:
                    per = getattr(s.student, 'billing_per_class', None) or 0
                total += int(per or 0)
            rows.append((st.name, classes, total))
        return rows

    t_rows = teacher_rows()
    s_rows = student_rows()

    # PDF 組み立て
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36
    )
    font_name = _register_jp_font()
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="JPTitle", fontName=font_name, fontSize=16, leading=20, spaceAfter=12))
    styles.add(ParagraphStyle(name="JPText", fontName=font_name, fontSize=10, leading=14, spaceAfter=6))

    story = []
    story.append(Paragraph("報酬・請求レポート", styles["JPTitle"]))
    story.append(Paragraph(f"対象期間: {start_date} 〜 {end_date}（集計月: {ym_str}）", styles["JPText"]))
    story.append(Spacer(1, 8))

    # 講師テーブル
    story.append(Paragraph("講師別（報酬）", styles["JPText"]))
    t_data = [["講師名", "コマ数", "合計報酬(円)"]]
    t_data += [[name, f"{classes}", f"{total:,}"] for name, classes, total in t_rows]
    if len(t_data) == 1:
        t_data.append(["（講師が未登録）", "0", "0"])

    t_table = Table(t_data, colWidths=[240, 80, 120])
    t_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f0f0")),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_table)
    story.append(Spacer(1, 12))

    # 生徒テーブル
    story.append(Paragraph("生徒別（請求）", styles["JPText"]))
    s_data = [["生徒名", "コマ数", "合計請求(円)"]]
    s_data += [[name, f"{classes}", f"{total:,}"] for name, classes, total in s_rows]
    if len(s_data) == 1:
        s_data.append(["（生徒が未登録）", "0", "0"])

    s_table = Table(s_data, colWidths=[240, 80, 120])
    s_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f0f0")),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(s_table)

    doc.build(story)

    pdf = buffer.getvalue()
    buffer.close()
    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename=reward_{ym_str}.pdf'
    return resp

@login_required
@user_passes_test(is_admin)
def reward_report_detail(request, teacher_id):
    """
    指定講師の対象月の確定授業明細。
    GET: ym=YYYY-MM（未指定は当月）
    """
    ym = request.GET.get("ym")
    today = date.today()
    if ym and parse_ym(ym):
        year, month = parse_ym(ym)
    else:
        year, month = today.year, today.month

    start_date, end_date = closing_range(year, month)

    # 明細は「カルテ提出済（is_confirmed=True）」のみ対象
    qs = (
        ClassSchedule.objects
        .filter(
            class_date__range=[start_date, end_date],
            teacher_id=teacher_id,
            karte__is_confirmed=True,
        )
        .select_related("teacher", "student", "subject")
    )

    # 1行ずつ請求/報酬を算出（ビュー側で計算）
    rows = []
    total_reward = 0
    total_fee = 0
    for s in qs:
        # 生徒請求（1コマ）
        billing = s.student.billing_per_class or 0

        # 講師報酬（1コマ）
        rc = s.student.reward_category
        if rc and rc.category == "custom":
            reward = s.student.custom_reward_per_class or 0
        else:
            reward = (rc.reward_per_class if rc and rc.reward_per_class is not None else 0)

        rows.append({
            "date": s.class_date,
            "start": s.start_time,
            "end": s.end_time,
            "student": s.student.name,
            "subject": getattr(s.subject, "name", ""),
            "billing": billing,
            "reward": reward,
            "schedule_id": s.id,
        })
        total_reward += reward
        total_fee    += billing

    teacher_name = getattr(qs.first().teacher, "name", f"ID:{teacher_id}") if qs.exists() else ""

    ctx = {
        "selected_ym": f"{year}-{month:02d}",
        "start_date": start_date, "end_date": end_date,
        "teacher_id": teacher_id, "teacher_name": teacher_name,
        "rows": rows,
        "total_reward": total_reward,
        "total_fee": total_fee,
    }
    return render(request, "admin_portal/rewards/reward_report_detail.html", ctx)

@login_required
@user_passes_test(is_admin)
def reward_settings_top(request):
    reward_cats = RewardCategory.objects.all().order_by('category')
    billing_cats = BillingCategory.objects.all().order_by('category')
    return render(
        request,
        'admin_portal/rewards/reward_settings_top.html',
        {'reward_cats': reward_cats, 'billing_cats': billing_cats},
    )

@login_required
@user_passes_test(is_admin)
def reward_category_list(request):
    cats = RewardCategory.objects.all().order_by('category')
    return render(request, 'admin_portal/rewards/reward_category_list.html', {'cats': cats})


@login_required
@user_passes_test(is_admin)
def billing_category_list(request):
    cats = BillingCategory.objects.all().order_by('category')
    return render(request, 'admin_portal/rewards/billing_category_list.html', {'cats': cats})

@login_required
@user_passes_test(is_admin)
def reward_category_edit(request, pk):
    cat = get_object_or_404(RewardCategory, pk=pk)
    if request.method == 'POST':
        form = RewardCategoryForm(request.POST, instance=cat)
        if form.is_valid():
            form.save()
            messages.success(request, '報酬カテゴリを更新しました。')
            return redirect('admin_portal:reward_category_list')
    else:
        form = RewardCategoryForm(instance=cat)
    return render(request, 'admin_portal/rewards/reward_category_edit.html', {'form': form, 'cat': cat})


@login_required
@user_passes_test(is_admin)
def billing_category_edit(request, pk):
    cat = get_object_or_404(BillingCategory, pk=pk)
    if request.method == 'POST':
        form = BillingCategoryForm(request.POST, instance=cat)
        if form.is_valid():
            form.save()
            messages.success(request, '請求カテゴリを更新しました。')
            return redirect('admin_portal:billing_category_list')
    else:
        form = BillingCategoryForm(instance=cat)
    return render(request, 'admin_portal/rewards/billing_category_edit.html', {'form': form, 'cat': cat})

@login_required
@user_passes_test(is_admin)
def student_reward_list(request):
    q_name = request.GET.get('name', '').strip()
    q_grade = request.GET.get('grade', '').strip()

    qs = StudentProfile.objects.select_related('reward_category', 'billing_category').all().order_by('name')
    if q_name:
        qs = qs.filter(name__icontains=q_name)
    if q_grade:
        qs = qs.filter(grade=q_grade)

    paginator = Paginator(qs, 20)
    page = request.GET.get('page')
    page_obj = paginator.get_page(page)

    grades = [(g, label) for g, label in StudentProfile._meta.get_field('grade').choices]

    return render(request, 'admin_portal/rewards/student_reward_list.html', {
        'page_obj': page_obj,
        'q_name': q_name,
        'q_grade': q_grade,
        'grades': grades,
    })

@login_required
@user_passes_test(is_admin)
def student_reward_edit(request, pk):
    stu = get_object_or_404(StudentProfile, pk=pk)
    if request.method == 'POST':
        form = StudentRewardForm(request.POST, instance=stu)
        if form.is_valid():
            form.save()
            messages.success(request, '生徒の請求・報酬設定を更新しました。')
            return redirect('admin_portal:student_reward_list')
    else:
        form = StudentRewardForm(instance=stu)
    return render(request, 'admin_portal/rewards/student_reward_edit.html', {'form': form, 'stu': stu})

@login_required
@user_passes_test(is_admin)
def reward_category_create(request):
    if request.method == 'POST':
        form = RewardCategoryCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '報酬カテゴリを作成しました。')
            return redirect('admin_portal:reward_category_list')
    else:
        form = RewardCategoryCreateForm()
    return render(request, 'admin_portal/rewards/reward_category_form.html', {'form': form, 'mode': 'create'})


@login_required
@user_passes_test(is_admin)
def billing_category_create(request):
    if request.method == 'POST':
        form = BillingCategoryCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '請求カテゴリを作成しました。')
            return redirect('admin_portal:billing_category_list')
    else:
        form = BillingCategoryCreateForm()
    return render(
        request,
        'admin_portal/rewards/billing_category_form.html',
        {'form': form, 'mode': 'create'},
    )

@login_required
@user_passes_test(is_admin)
def account_status_list(request):
    form = AccountStatusSearchForm(request.GET or None)

    qs = (User.objects
          .select_related('userprofile', 'teacherprofile', 'adminprofile', 'studentprofile')  # 逆OneToOneもOK
          .order_by('username'))

    if form.is_valid():
        q = (form.cleaned_data.get('q') or '').strip()
        if q:
            qs = qs.filter(
                Q(username__icontains=q) |
                Q(teacherprofile__name__icontains=q) |
                Q(studentprofile__name__icontains=q) |
                Q(adminprofile__name__icontains=q)
            )
        utype = form.cleaned_data.get('user_type')
        if utype:
            qs = qs.filter(userprofile__user_type=utype)

        if form.cleaned_data.get('only_locked'):
            qs = qs.filter(userprofile__is_locked=True)
    else:
        # 初期はロック中のみ
        qs = qs.filter(userprofile__is_locked=True)

    page_obj = Paginator(qs, 25).get_page(request.GET.get('page'))

    def _profile_name(user, attr):
        try:
            profile = getattr(user, attr)
        except ObjectDoesNotExist:
            return None
        return getattr(profile, 'name', None)

    for user in page_obj.object_list:
        name = (
            _profile_name(user, 'teacherprofile')
            or _profile_name(user, 'studentprofile')
            or _profile_name(user, 'adminprofile')
        )
        if not name:
            full_name = user.get_full_name()
            name = full_name or user.username
        user.display_name = name

    return render(request, 'admin_portal/accounts/account_status_list.html', {
        'form': form, 'page_obj': page_obj,
    })

@login_required
@user_passes_test(is_admin)
def karte_pdf_admin(request, schedule_id: int):
    """管理者向け：カルテPDFダウンロード（講師制限なし）"""
    schedule = get_object_or_404(
        ClassSchedule.objects.select_related('student', 'subject', 'teacher'),
        id=schedule_id,
    )
    karte, _ = ClassKarte.objects.get_or_create(
        schedule=schedule,
        defaults={
            "class_date": schedule.class_date,
            "student": schedule.student,
            "teacher": schedule.teacher,
            "subject": schedule.subject,
        },
    )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    font_name = _register_jp_font()
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="JPTitle", fontName=font_name, fontSize=16, leading=20, spaceAfter=12))
    styles.add(ParagraphStyle(name="JPText", fontName=font_name, fontSize=10, leading=14, spaceAfter=6))

    def ev_label(v):
        return {"more":"もう少し","good":"よくできました","great":"大変よくできました"}.get(v, "-")

    story = []
    story.append(Paragraph("授業カルテ", styles["JPTitle"]))
    meta_tbl = Table([
        ["授業日", str(karte.class_date or schedule.class_date)],
        ["講師", getattr(schedule.teacher, 'name', '-')],
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
    return resp

@login_required
@user_passes_test(is_admin)
def karte_view_admin(request, schedule_id: int):
    """管理者向け: カルテ閲覧（読み取り専用HTML）。"""
    schedule = get_object_or_404(
        ClassSchedule.objects.select_related('student', 'subject', 'teacher'),
        id=schedule_id,
    )
    karte, _ = ClassKarte.objects.get_or_create(
        schedule=schedule,
        defaults={
            "class_date": schedule.class_date,
            "student": schedule.student,
            "teacher": schedule.teacher,
            "subject": schedule.subject,
        },
    )
    return render(
        request,
        'admin_portal/schedules/karte_detail.html',
        {"schedule": schedule, "karte": karte},
    )

@login_required
@user_passes_test(is_admin)
def unlock_user(request, user_id):
    forbidden = _demo_staff_sensitive_forbidden(request)
    if forbidden:
        return forbidden
    user = get_object_or_404(User.objects.select_related('userprofile'), id=user_id)
    if request.method == 'POST':
        up = user.userprofile
        up.is_locked = False
        up.failed_login_attempts = 0
        up.save()
        messages.success(request, f'ユーザー {user.username} のロックを解除しました。')
    return redirect('admin_portal:account_status_list')

@login_required
@user_passes_test(is_admin)
def reset_fail_count(request, user_id):
    forbidden = _demo_staff_sensitive_forbidden(request)
    if forbidden:
        return forbidden
    user = get_object_or_404(User.objects.select_related('userprofile'), id=user_id)
    if request.method == 'POST':
        up = user.userprofile
        up.failed_login_attempts = 0
        up.save()
        messages.success(request, f'ユーザー {user.username} の失敗回数をリセットしました。')
    return redirect('admin_portal:account_status_list')


def _gen_password(length=12):
    alphabet = string.ascii_letters + string.digits
    pwd = "".join(secrets.choice(alphabet) for _ in range(length))
    if not any(c.islower() for c in pwd):
        pwd = "a" + pwd[1:]
    if not any(c.isupper() for c in pwd):
        pwd = "A" + pwd[1:]
    if not any(c.isdigit() for c in pwd):
        pwd = "7" + pwd[1:]
    return pwd


@login_required
@user_passes_test(is_admin)
def reset_locked_account(request, user_id):
    forbidden = _demo_staff_sensitive_forbidden(request)
    if forbidden:
        return forbidden
    target = get_object_or_404(User, pk=user_id)

    profile = getattr(target, "userprofile", None)
    is_locked = bool(getattr(profile, "is_locked", False) or getattr(target, "is_active", True) is False)

    if request.method == "GET":
        new_pwd = _gen_password()
        token = dumps({"uid": target.id, "pwd": new_pwd})
        ctx = {"target": target, "generated_password": new_pwd, "token": token, "is_locked": is_locked}
        return render(request, "admin_portal/accounts/reset_locked_account_confirm.html", ctx)

    token = request.POST.get("token")
    copied = request.POST.get("copied") == "on"
    if not copied:
        messages.error(request, "初期パスワードを控えたことを確認してください。")
        return redirect("admin_portal:reset_locked_account", user_id=user_id)

    try:
        data = loads(token, max_age=600)
    except (BadSignature, SignatureExpired):
        messages.error(request, "トークンが無効です。やり直してください。")
        return redirect("admin_portal:reset_locked_account", user_id=user_id)

    if int(data.get("uid")) != target.id:
        messages.error(request, "トークンの対象が一致しません。")
        return redirect("admin_portal:reset_locked_account", user_id=user_id)

    new_pwd = data.get("pwd")
    if not new_pwd:
        messages.error(request, "パスワードが生成されていません。")
        return redirect("admin_portal:reset_locked_account", user_id=user_id)

    target.set_password(new_pwd)
    if profile:
        profile.is_locked = False
        profile.failed_login_attempts = 0
        profile.save(update_fields=["is_locked", "failed_login_attempts"])
    if hasattr(target, "is_active") and target.is_active is False:
        target.is_active = True
    target.last_login = None
    target.save()

    messages.success(request, "パスワードを初期化しました。ユーザーに新しい初期パスワードを配布してください。")
    return redirect("admin_portal:account_status_list")

@login_required
@user_passes_test(is_admin)
def schedule_create_view(request):
    is_error = False
    if request.method == 'POST':
        form = ClassScheduleForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            if cd.get("class_date") and cd.get("start_time") and cd.get("end_time") and cd.get("teacher"):
                if has_conflict(
                    cd["class_date"],
                    cd["start_time"],
                    cd["end_time"],
                    cd["teacher"].id,
                    cd["student"].id,
                ):
                    messages.error(
                        request,
                        "同一時間帯に既存の予定があり、重複しています。（教師または生徒のどちらかが重複）",
                    )
                    is_error = True
                else:
                    form.save()
                    messages.success(request, "授業を登録しました。")
                    return redirect('admin_portal:schedule_board')
            else:
                form.save()
                messages.success(request, "授業を登録しました。")
                return redirect('admin_portal:schedule_board')
        else:
            messages.error(request, "入力にエラーがあります。各項目を確認してください。")
            is_error = True
    else:
        form = ClassScheduleForm()
    status = 400 if is_error else 200
    return render(request, 'admin_portal/schedules/schedule_create.html', {'form': form}, status=status)

@login_required
@user_passes_test(is_admin)
def teacher_list_view(request):
    qs = TeacherProfile.objects.select_related('user').prefetch_related('subjects').order_by('name')
    # 簡易検索（氏名/電話/メール）
    q = request.GET.get('q')
    if q:
        from django.db.models import Q
        qs = qs.filter(Q(name__icontains=q) | Q(phone__icontains=q) | Q(email__icontains=q))
    # ページング
    paginator = Paginator(qs, 20)
    page = request.GET.get('page')
    teachers = paginator.get_page(page)
    return render(request, 'admin_portal/teachers/teacher_list.html', {'teachers': teachers, 'q': q or ''})

@login_required
@user_passes_test(is_admin)
def teacher_detail_view(request, pk):
    teacher = get_object_or_404(TeacherProfile.objects.select_related('user').prefetch_related('subjects'), pk=pk)
    # 紐づく授業も少しだけ表示（最近10件）
    schedules = (ClassSchedule.objects
                 .select_related('student','subject')
                 .filter(teacher=teacher)
                 .order_by('-class_date','-start_time')[:10])
    return render(request, 'admin_portal/teachers/teacher_detail.html', {
        'teacher': teacher,
        'schedules': schedules,
    })

@login_required
@user_passes_test(is_admin)
def teacher_edit_view(request, pk):
    teacher = get_object_or_404(TeacherProfile, pk=pk)
    if request.method == 'POST':
        form = TeacherEditForm(request.POST, instance=teacher)
        if form.is_valid():
            form.save()
            messages.success(request, '講師情報を更新しました。')
            return redirect('admin_portal:teacher_detail', pk=teacher.pk)
        else:
            messages.error(request, '入力内容にエラーがあります。')
    else:
        form = TeacherEditForm(instance=teacher)
    return render(request, 'admin_portal/teachers/teacher_edit.html', {'form': form, 'teacher': teacher})


@login_required
@user_passes_test(is_admin)
def teacher_delete_view(request, pk):
    teacher = get_object_or_404(TeacherProfile.objects.select_related('user'), pk=pk)

    guard = globals().get("_demo_staff_sensitive_forbidden")
    if callable(guard):
        forbidden = guard(request)
        if forbidden:
            return forbidden

    assignment_count = TeacherStudentAssignment.objects.filter(teacher=teacher).count()
    schedule_count = ClassSchedule.objects.filter(teacher=teacher).count()
    try:
        teacher_username = teacher.user.username
    except User.DoesNotExist:
        teacher_username = ""

    if request.method == 'POST':
        teacher_name = teacher.name
        try:
            linked_user = teacher.user
        except User.DoesNotExist:
            linked_user = None
        with transaction.atomic():
            with demo_delete_override():
                if linked_user:
                    linked_user.delete()
                else:
                    teacher.delete()
        messages.success(request, f'講師「{teacher_name}」を削除しました。')
        return redirect('admin_portal:teacher_list')

    return render(
        request,
        'admin_portal/teachers/teacher_confirm_delete.html',
        {
            'teacher': teacher,
            'assignment_count': assignment_count,
            'schedule_count': schedule_count,
            'teacher_username': teacher_username,
        },
    )


@login_required
@user_passes_test(is_admin)
def student_list_view(request):
    qs = StudentProfile.objects.select_related('user','reward_category').prefetch_related('subjects').order_by('name')
    q = request.GET.get('q')
    if q:
        from django.db.models import Q
        qs = qs.filter(Q(name__icontains=q) | Q(phone__icontains=q) | Q(email__icontains=q))
    paginator = Paginator(qs, 20)
    page = request.GET.get('page')
    students = paginator.get_page(page)
    return render(request, 'admin_portal/students/student_list.html', {'students': students, 'q': q or ''})


@login_required
@user_passes_test(is_admin)
def student_delete_view(request, pk):
    student = get_object_or_404(StudentProfile.objects.select_related('user'), pk=pk)

    guard = globals().get("_demo_staff_sensitive_forbidden")
    if callable(guard):
        forbidden = guard(request)
        if forbidden:
            return forbidden

    assignment_count = TeacherStudentAssignment.objects.filter(student=student).count()
    schedule_count = ClassSchedule.objects.filter(student=student).count()
    try:
        student_username = student.user.username
    except User.DoesNotExist:
        student_username = ""

    if request.method == 'POST':
        student_name = student.name
        try:
            linked_user = student.user
        except User.DoesNotExist:
            linked_user = None
        with transaction.atomic():
            with demo_delete_override():
                if linked_user:
                    linked_user.delete()
                else:
                    student.delete()
        messages.success(request, f'生徒「{student_name}」を削除しました。')
        return redirect('admin_portal:student_list')

    return render(
        request,
        'admin_portal/students/student_confirm_delete.html',
        {
            'student': student,
            'assignment_count': assignment_count,
            'schedule_count': schedule_count,
            'student_username': student_username,
        },
    )

@login_required
@user_passes_test(is_admin)
def student_detail_view(request, pk):
    student = get_object_or_404(
    StudentProfile.objects.select_related('user', 'reward_category').prefetch_related('subjects'),
    pk=pk
    )
    schedules = (ClassSchedule.objects
                 .select_related('teacher','subject')
                 .filter(student=student)
                 .order_by('-class_date','-start_time')[:10])
    return render(request, 'admin_portal/students/student_detail.html', {
        'student': student,
        'schedules': schedules,
    })

@login_required
@user_passes_test(is_admin)
def student_edit_view(request, pk):
    student = get_object_or_404(StudentProfile, pk=pk)
    if request.method == 'POST':
        form = StudentEditForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, '生徒情報を更新しました。')
            return redirect('admin_portal:student_detail', pk=student.pk)
        else:
            messages.error(request, '入力内容にエラーがあります。')
    else:
        form = StudentEditForm(instance=student)
    return render(request, 'admin_portal/students/student_edit.html', {'form': form, 'student': student})

# 締めの作成（集計→スナップショット保存）
@login_required
@user_passes_test(is_admin)
def reward_close_create_view(request):
    ym = request.GET.get("ym")
    today = date.today()
    if ym and parse_ym(ym):
        year, month = parse_ym(ym)
    else:
        year, month = today.year, today.month

    start_date, end_date = closing_range(year, month)
    if RewardClosing.objects.filter(year=year, month=month).exists():
        messages.warning(request, f"{year}-{month:02d} はすでに締め済みです。")
        return redirect("admin_portal:reward_report")

    closing = RewardClosing.objects.create(
        year=year, month=month, start_date=start_date, end_date=end_date, closed_by=request.user
    )

    # 該当期間の確定授業
    qs = ClassSchedule.objects.filter(
        status=ClassSchedule.STATUS_DONE, class_date__range=[start_date, end_date]
    ).select_related("teacher", "student", "student__reward_category")

    # 先生×（生徒ごとの単価）の合計
    # ※生徒ごとに billing/報酬が異なる想定なので、単価は集約時に合算のみ
    per_teacher = {}
    for s in qs:
        # 講師報酬は StudentProfile から決まる（あなたのプロジェクトの仕様に合わせて）
        unit = s.student.custom_reward_per_class or \
               (s.student.reward_category.reward_per_class if s.student.reward_category else 0)
        t = s.teacher_id
        if t not in per_teacher:
            per_teacher[t] = {"teacher": s.teacher, "count": 0, "total": 0}
        per_teacher[t]["count"] += 1
        per_teacher[t]["total"] += int(unit or 0)

    # 明細保存
    for data in per_teacher.values():
        RewardClosingTeacher.objects.create(
            closing=closing,
            teacher=data["teacher"],
            confirmed_count=data["count"],
            unit_reward=None,  # 生徒により単価変動する設計のため
            total_reward=data["total"],
        )

    messages.success(request, f"{year}-{month:02d} の締めを作成しました。")
    return redirect("admin_portal:reward_close_detail", closing_id=closing.id)

# 締めの閲覧
@login_required
@user_passes_test(is_admin)
def reward_close_detail_view(request, closing_id):
    closing = get_object_or_404(RewardClosing, id=closing_id)
    rows = closing.teachers.select_related("teacher").order_by("teacher__name")
    return render(request, "admin_portal/rewards/reward_close_detail.html", {
        "closing": closing, "rows": rows,
    })

# CSV出力
@login_required
@user_passes_test(is_admin)
def reward_close_export_csv(request, closing_id):
    closing = get_object_or_404(RewardClosing, id=closing_id)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    filename = f"reward_{closing.year}{closing.month:02d}.csv"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)
    writer.writerow(["講師名","確定コマ数","合計（円）"])
    for r in closing.teachers.select_related("teacher"):
        writer.writerow([r.teacher.name, r.confirmed_count, r.total_reward])
    return response

# PDF出力（ReportLab）
@login_required
@user_passes_test(is_admin)
def reward_close_export_pdf(request, closing_id):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    from reportlab.lib.utils import simpleSplit

    closing = get_object_or_404(RewardClosing, id=closing_id)

    response = HttpResponse(content_type='application/pdf')
    filename = f"reward_{closing.year}{closing.month:02d}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    y = height - 20*mm
    title = f"報酬締め {closing.year}-{closing.month:02d}  ({closing.start_date} ～ {closing.end_date})"
    p.setFont("HeiseiKakuGo-W5", 14) if "HeiseiKakuGo-W5" in p.getAvailableFonts() else p.setFont("Helvetica", 14)
    p.drawString(20*mm, y, title); y -= 12*mm

    p.setFont("Helvetica", 10)
    p.drawString(20*mm, y, "講師名"); p.drawString(90*mm, y, "確定コマ数"); p.drawString(130*mm, y, "合計（円）"); y -= 8*mm
    p.line(20*mm, y, 190*mm, y); y -= 5*mm

    total_all = 0
    for r in closing.teachers.select_related("teacher"):
        if y < 20*mm:
            p.showPage(); y = height - 20*mm
        p.drawString(20*mm, y, r.teacher.name)
        p.drawRightString(115*mm, y, str(r.confirmed_count))
        p.drawRightString(180*mm, y, f"{r.total_reward:,}")
        total_all += r.total_reward
        y -= 6*mm

    y -= 6*mm
    p.line(120*mm, y, 190*mm, y); y -= 6*mm
    p.setFont("Helvetica-Bold", 11)
    p.drawString(120*mm, y, "合計")
    p.drawRightString(180*mm, y, f"{total_all:,}")

    p.showPage()
    p.save()
    return response

@login_required
@user_passes_test(is_admin)
def schedule_bulk_update_view(request):
    if request.method != "POST":
        return redirect("admin_portal:schedule_board")
    ids = request.POST.getlist("ids")
    action = request.POST.get("action")
    if not ids or not action:
        messages.error(request, "対象と操作を選択してください。")
        return redirect("admin_portal:schedule_board")

    qs = ClassSchedule.objects.filter(id__in=ids)
    if action == "pending":
        # ステータスのみ保留へ（カルテ確定は解除しない）
        updated = qs.update(status=ClassSchedule.STATUS_PENDING)
        messages.success(request, f"{updated}件を保留に変更しました。")
    elif action == "scheduled":
        # 未実施へ戻す際は、確定済みカルテがあれば解除して整合させる
        count = 0
        for s in qs.select_related("karte"):
            try:
                if hasattr(s, "karte") and s.karte and s.karte.is_confirmed:
                    s.karte.reopen()
                s.status = ClassSchedule.STATUS_SCHEDULED
                s.save(update_fields=["status"])
                count += 1
            except Exception:
                continue
        messages.success(request, f"{count}件を未実施に変更しました（必要に応じて確定解除）。")
    elif action == "done":
        # 実施済みにする場合はカルテを確定して整合させる
        count = 0
        for s in qs.select_related("karte", "teacher", "student", "subject"):
            try:
                karte, _ = ClassKarte.objects.get_or_create(
                    schedule=s,
                    defaults={
                        "class_date": s.class_date,
                        "student": s.student,
                        "teacher": s.teacher,
                        "subject": s.subject,
                    },
                )
                if not karte.is_confirmed:
                    karte.confirm(by=None)
                # confirm() 内で status=done に更新される実装だが、念のため明示
                if s.status != ClassSchedule.STATUS_DONE:
                    s.status = ClassSchedule.STATUS_DONE
                    s.save(update_fields=["status"])
                count += 1
            except Exception:
                continue
        messages.success(request, f"{count}件を実施済に変更しました（カルテ確定）。")
    elif action == "delete":
        count = qs.count()
        qs.delete()
        messages.success(request, f"{count}件を削除しました。")
    else:
        messages.error(request, "不明な操作です。")
    return redirect("admin_portal:schedule_board")

@login_required
@user_passes_test(is_admin)
def import_teachers_view(request):
    if request.method == "POST":
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            f = io.TextIOWrapper(request.FILES["file"].file, encoding="utf-8-sig")
            reader = csv.DictReader(f)
            created = 0
            for row in reader:
                t, _ = TeacherProfile.objects.get_or_create(
                    name=row.get("name","").strip(),
                    defaults=dict(
                        gender=row.get("gender","").strip() or "man",
                        age=int(row.get("age","0") or 0),
                        address=row.get("address",""),
                        phone=row.get("phone",""),
                        email=row.get("email",""),
                        school=row.get("school",""),
                        grade=row.get("grade",""),
                    )
                )
                subs = [s.strip() for s in row.get("subjects","").split(",") if s.strip()]
                if subs:
                    t.subjects.set(Subject.objects.filter(name__in=subs))
                created += 1
            messages.success(request, f"講師 {created} 件を取り込みました。")
            return redirect("admin_portal:teacher_list")
    else:
        form = CSVUploadForm()
    return render(request, "admin_portal/teachers/import_teachers.html", {"form": form})

@login_required
@user_passes_test(is_admin)
def import_students_view(request):
    if request.method == "POST":
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            f = io.TextIOWrapper(request.FILES["file"].file, encoding="utf-8-sig")
            reader = csv.DictReader(f)
            created = 0
            for row in reader:
                s, _ = StudentProfile.objects.get_or_create(
                    name=row.get("name","").strip(),
                    defaults=dict(
                        gender=row.get("gender","").strip() or "man",
                        age=int(row.get("age","0") or 0),
                        address=row.get("address",""),
                        phone=row.get("phone",""),
                        email=row.get("email",""),
                        school=row.get("school",""),
                        grade=row.get("grade",""),
                    )
                )
                subs = [x.strip() for x in row.get("subjects","").split(",") if x.strip()]
                if subs:
                    s.subjects.set(Subject.objects.filter(name__in=subs))
                created += 1
            messages.success(request, f"生徒 {created} 件を取り込みました。")
            return redirect("admin_portal:student_list")
    else:
        form = CSVUploadForm()
    return render(request, "admin_portal/students/import_students.html", {"form": form})


@login_required
def assignment_list_view(request):
    if not is_admin(request.user): return HttpResponseForbidden("権限がありません")
    teacher = request.GET.get("teacher", "")
    student = request.GET.get("student", "")
    q = request.GET.get("q", "").strip()
    page = request.GET.get("page", 1)

    qs = TeacherStudentAssignment.objects.select_related("teacher", "student").order_by("teacher__name", "student__name")

    if teacher:
        qs = qs.filter(teacher_id=teacher)
    if student:
        qs = qs.filter(student_id=student)
    if q:
        qs = qs.filter(Q(teacher__name__icontains=q) | Q(student__name__icontains=q))

    total = cached_count(qs, f"count:{request.get_full_path()}")
    paginator = Paginator(qs, 50)
    page_obj = paginator.get_page(page)

    teachers = TeacherProfile.objects.order_by("name").only("id", "name")
    students = StudentProfile.objects.order_by("name").only("id", "name")

    return render(request, "admin_portal/assignments/assignment_list.html", {
        "page_obj": page_obj, "paginator": paginator, "total": total,
        "teacher_id": teacher, "student_id": student, "q": q,
        "teachers": teachers, "students": students,
    })


@login_required
def assignment_create_view(request):
    if not is_admin(request.user): return HttpResponseForbidden("権限がありません")
    if request.method == "POST":
        form = AssignmentCreateForm(request.POST)
        if form.is_valid():
            t = form.cleaned_data["teacher"]
            s = form.cleaned_data["student"]
            subs = form.cleaned_data["subjects"]
            ass, _ = TeacherStudentAssignment.objects.get_or_create(teacher=t, student=s)
            if subs is not None:
                ass.subjects.set(subs)
            messages.success(request, "割当を作成しました。")
            return redirect("admin_portal:assignment_list")
    else:
        form = AssignmentCreateForm()
    return render(request, "admin_portal/assignments/assignment_create.html", {"form": form})


@login_required
def assignment_subjects_edit(request, assignment_id:int):
    if not is_admin(request.user): return HttpResponseForbidden("権限がありません")
    ass = get_object_or_404(TeacherStudentAssignment, pk=assignment_id)
    if request.method == "POST":
        ids = request.POST.getlist("subjects")
        ass.subjects.set(ids)
        messages.success(request, "担当科目を更新しました。")
        return redirect("admin_portal:assignment_list")
    subjects = Subject.objects.order_by("name")
    selected = set(ass.subjects.values_list("id", flat=True))
    return render(request, "admin_portal/assignments/assignment_subjects_edit.html", {
        "assignment": ass, "subjects": subjects, "selected": selected
    })


@login_required
def assignment_delete_view(request, pk: int):
    if not is_admin(request.user):
        return HttpResponseForbidden("権限がありません")
    obj = get_object_or_404(TeacherStudentAssignment, pk=pk)
    if request.method == "POST":
        obj.delete()
        return redirect("admin_portal:assignment_list")
    return render(
        request,
        "admin_portal/assignments/assignment_confirm_delete.html",
        {"obj": obj},
    )


@login_required
def assignment_manage_teacher(request, teacher_id: int):
    if not is_admin(request.user):
        return HttpResponseForbidden("権限がありません")
    teacher = get_object_or_404(TeacherProfile, pk=teacher_id)
    current = (
        TeacherStudentAssignment.objects.filter(teacher=teacher)
        .select_related("student")
        .order_by("student__name")
    )

    q = request.GET.get("q", "").strip()
    only_unassigned = request.GET.get("only_unassigned") == "1"

    students = StudentProfile.objects.order_by("name").only("id", "name")
    if q:
        students = students.filter(name__icontains=q)
    if only_unassigned:
        students = students.filter(teacherstudentassignment__isnull=True)

    if request.method == "POST":
        if request.POST.get("bulk_remove"):
            ids = request.POST.getlist("ids")
            TeacherStudentAssignment.objects.filter(id__in=ids, teacher=teacher).delete()
            return redirect("admin_portal:assignment_manage_teacher", teacher_id=teacher.id)
        sid = request.POST.get("student")
        if sid:
            TeacherStudentAssignment.objects.get_or_create(teacher=teacher, student_id=sid)
            return redirect("admin_portal:assignment_manage_teacher", teacher_id=teacher.id)

    return render(
        request,
        "admin_portal/assignments/assignment_manage_teacher.html",
        {
            "teacher": teacher,
            "current": current,
            "students": students,
            "q": q,
            "only_unassigned": only_unassigned,
        },
    )


@login_required
def assignment_manage_student(request, student_id: int):
    if not is_admin(request.user):
        return HttpResponseForbidden("権限がありません")
    student = get_object_or_404(StudentProfile, pk=student_id)
    current = (
        TeacherStudentAssignment.objects.filter(student=student)
        .select_related("teacher")
        .order_by("teacher__name")
    )

    q = request.GET.get("q", "").strip()
    only_unassigned = request.GET.get("only_unassigned") == "1"

    teachers = TeacherProfile.objects.order_by("name").only("id", "name")
    if q:
        teachers = teachers.filter(name__icontains=q)
    if only_unassigned:
        teachers = teachers.filter(teacherstudentassignment__isnull=True)

    if request.method == "POST":
        if request.POST.get("bulk_remove"):
            ids = request.POST.getlist("ids")
            TeacherStudentAssignment.objects.filter(id__in=ids, student=student).delete()
            return redirect("admin_portal:assignment_manage_student", student_id=student.id)
        tid = request.POST.get("teacher")
        if tid:
            TeacherStudentAssignment.objects.get_or_create(student=student, teacher_id=tid)
            return redirect("admin_portal:assignment_manage_student", student_id=student.id)

    return render(
        request,
        "admin_portal/assignments/assignment_manage_student.html",
        {
            "student": student,
            "current": current,
            "teachers": teachers,
            "q": q,
            "only_unassigned": only_unassigned,
        },
    )


def assignment_template_csv(request):
    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = 'attachment; filename="assignment_template.csv"'
    resp.write("\ufeff")
    writer = csv.writer(resp)
    writer.writerow(["teacher_username", "student_username"])
    writer.writerow(["taro", "hanako"])
    return resp


@login_required
def attendance_dashboard(request):
    if not is_admin(request.user):
        return HttpResponseForbidden("権限がありません")
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")
    qs = ClassSchedule.objects.all()
    if date_from:
        qs = qs.filter(class_date__gte=date_from)
    if date_to:
        qs = qs.filter(class_date__lte=date_to)
    qs = qs.select_related("subject")
    total = qs.count()
    held = qs.filter(is_held=True).count()
    absent = qs.filter(is_absent=True).count()
    tardy = qs.filter(is_tardy=True).count()
    by_subject = (
        qs.values("subject__name")
        .annotate(
            total=Count("id"),
            absent=Count("id", filter=Q(is_absent=True)),
            tardy=Count("id", filter=Q(is_tardy=True)),
        )
        .order_by("subject__name")
    )
    return render(
        request,
        "admin_portal/schedules/attendance_dashboard.html",
        {
            "total": total,
            "held": held,
            "absent": absent,
            "tardy": tardy,
            "by_subject": by_subject,
            "date_from": date_from,
            "date_to": date_to,
        },
    )


@login_required
def assignment_bulk_view(request):
    if not is_admin(request.user):
        return HttpResponseForbidden("権限がありません")

    if request.method == "POST" and request.POST.get("confirm"):
        csvdata = request.POST.get("csvdata", "")
        reader = csv.DictReader(io.StringIO(csvdata))
        headers = {h.strip().lower() for h in reader.fieldnames or []}
        use_username = {"teacher_username", "student_username"} <= headers
        created = skipped = errors = 0
        try:
            with transaction.atomic():
                for row in reader:
                    try:
                        if use_username:
                            t = TeacherProfile.objects.select_related("user").get(
                                user__username=row["teacher_username"].strip()
                            )
                            s = StudentProfile.objects.select_related("user").get(
                                user__username=row["student_username"].strip()
                            )
                        else:
                            t = TeacherProfile.objects.get(pk=int(row["teacher_id"]))
                            s = StudentProfile.objects.get(pk=int(row["student_id"]))
                        obj, created_flag = TeacherStudentAssignment.objects.get_or_create(
                            teacher=t, student=s
                        )
                        created += 1 if created_flag else 0
                        if not created_flag:
                            skipped += 1
                    except Exception:
                        errors += 1
                        raise
        except Exception:
            messages.error(request, "エラーが発生したためロールバックしました。")
            return redirect("admin_portal:assignment_bulk")
        messages.success(request, f"作成: {created}, スキップ: {skipped}")
        return redirect("admin_portal:assignment_list")

    if request.method == "POST" and request.POST.get("preview") and request.FILES.get("file"):
        file = request.FILES["file"].read().decode("utf-8")
        reader = csv.DictReader(io.StringIO(file))
        headers = {h.strip().lower() for h in reader.fieldnames or []}
        use_username = {"teacher_username", "student_username"} <= headers
        rows = []
        has_error = False
        for row in reader:
            status = "OK"
            error = ""
            try:
                if use_username:
                    t = TeacherProfile.objects.select_related("user").get(
                        user__username=row["teacher_username"].strip()
                    )
                    s = StudentProfile.objects.select_related("user").get(
                        user__username=row["student_username"].strip()
                    )
                    if TeacherStudentAssignment.objects.filter(teacher=t, student=s).exists():
                        status = "SKIP"
                else:
                    t = TeacherProfile.objects.get(pk=int(row["teacher_id"]))
                    s = StudentProfile.objects.get(pk=int(row["student_id"]))
                    if TeacherStudentAssignment.objects.filter(teacher=t, student=s).exists():
                        status = "SKIP"
            except Exception as e:
                status = "ERROR"
                error = str(e)
                has_error = True
            rows.append({"row": row, "status": status, "error": error})
        return render(
            request,
            "admin_portal/assignments/assignment_bulk.html",
            {"preview": True, "rows": rows, "csvdata": file, "has_error": has_error},
        )

    return render(request, "admin_portal/assignments/assignment_bulk.html", {})


@login_required
def karte_reopen_view(request, karte_id: int):
    if not is_admin(request.user):
        return HttpResponseForbidden("権限がありません")
    karte = get_object_or_404(ClassKarte, pk=karte_id)
    karte.reopen()
    return redirect("admin_portal:admin_dashboard")


@login_required
def schedule_board_view(request):
    if not is_admin(request.user):
        return HttpResponseForbidden("権限がありません")

    q = (request.GET.get("q") or "").strip()
    base = ClassSchedule.objects.select_related("teacher", "student", "subject").order_by(
        "-class_date", "-start_time", "-id"
    )
    if q:
        base = base.filter(
            Q(student__name__icontains=q)
            | Q(teacher__name__icontains=q)
            | Q(subject__name__icontains=q)
        )

    pending_qs = base.filter(status="pending")
    scheduled_qs = base.filter(status="scheduled")
    done_qs = base.filter(status="done")

    p1 = Paginator(pending_qs, 10).get_page(request.GET.get("p1"))
    p2 = Paginator(scheduled_qs, 10).get_page(request.GET.get("p2"))
    p3 = Paginator(done_qs, 10).get_page(request.GET.get("p3"))

    return render(
        request,
        "admin_portal/schedules/schedule_board.html",
        {"q": q, "p1": p1, "p2": p2, "p3": p3},
    )


@login_required
def access_log_list_view(request):
    if not is_admin(request.user):
        return HttpResponseForbidden("権限がありません")

    q = (request.GET.get("q") or "").strip()
    role = (request.GET.get("role") or "").strip()
    qs = AccessLog.objects.select_related("user").order_by("-at")
    if q:
        qs = qs.filter(path__icontains=q)
    if role:
        qs = qs.filter(role=role)
    page = Paginator(qs, 50).get_page(request.GET.get("p"))
    return render(
        request,
        "admin_portal/accounts/access_logs.html",
        {"page": page, "q": q, "role": role},
    )
