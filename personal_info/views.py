from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from .models import Subject, ClassSchedule, TeachingMaterial
from .forms import SubjectForm
from admin_portal.forms import ClassScheduleForm

@login_required
@user_passes_test(lambda u: u.is_authenticated and hasattr(u, 'userprofile'))
def material_search_api(request):
    q = request.GET.get("q","").strip()
    if not q:
        return JsonResponse({"results":[]})
    hits = list(TeachingMaterial.objects.filter(title__icontains=q).values("id","title")[:10])
    return JsonResponse({"results": hits})

#登録科目一覧
@login_required
def subject_list(request):
    subjects = Subject.objects.all()
    if request.method == 'POST':
        form = SubjectForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('personal_info:subject_list')
    else:
        form = SubjectForm()
    return render(request, 'admin_portal/subject_list.html', {'subjects':subjects, 'form':form})

#授業予定編集
@login_required
def edit_schedule_view(request, schedule_id):
    schedule = get_object_or_404(ClassSchedule, id=schedule_id)

    #講師の場合は担当以外弾かれる
    if request.user.userprofile.user_type == 'teacher':
        if schedule.teacher.user != request.user:
            return redirect('permission_denied') #権限拒否ページ
        
    if request.method == 'POST':
        form = ClassScheduleForm(request.POST, instance=schedule)
        if form.is_valid():
            form.save()
            if request.user.userprofile.user_type == 'admin':
                return redirect('admin_portal:schedule_board') #管理者用一覧ページ
            else:
                return redirect('teacher_portal:schedule_board') #講師用一覧ページ
    else:
        form = ClassScheduleForm(instance=schedule)
    return render(request, 'personal_info/edit_schedule.html', {'form':form, 'schedule':schedule})

#登録教材一覧
@login_required
def material_list_view(request):
    materials = TeachingMaterial.objects.all().order_by('-created_at')
    profile = getattr(request.user, "userprofile", None)
    user_type = getattr(profile, "user_type", "")
    if user_type == "admin":
        edit_url_name = "admin_portal:material_edit"
        create_url_name = "admin_portal:material_create"
    elif user_type == "teacher":
        edit_url_name = "teacher_portal:teacher_material_edit"
        create_url_name = "teacher_portal:teacher_material_create"
    else:
        edit_url_name = ""
        create_url_name = ""

    return render(
        request,
        'personal_info/material_list.html',
        {
            'materials': materials,
            'user_type': user_type,
            'material_edit_url_name': edit_url_name,
            'material_create_url_name': create_url_name,
        },
    )
