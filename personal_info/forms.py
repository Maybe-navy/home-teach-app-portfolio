from django import forms
from django.core.exceptions import ValidationError
from .models import (
    Subject,
    ClassSchedule,
    TeachingMaterial,
    StudentProfile,
    MaterialUsage,
    TeacherStudentAssignment,
)


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['name']

class MaterialList(forms.ModelForm):
    class Meta:
        model = TeachingMaterial
        fields = ['title', 'subject', 'grade', 'publisher']

class ClassScheduleForm(forms.ModelForm):
    class_date = forms.DateField(
        label="授業日",
        widget=forms.DateInput(attrs={"type": "date"})
    )
    start_time = forms.TimeField(
        label="授業開始時刻",
        widget=forms.TimeInput(attrs={"type": "time"})
    )
    end_time = forms.TimeField(
        label="授業終了時刻",
        widget=forms.TimeInput(attrs={"type": "time"})
    )

    class Meta:
        model = ClassSchedule
        fields = [
            "teacher",
            "student",
            "subject",
            "class_date",
            "start_time",
            "end_time",
            "status",
            "material",
            "karte_summary",
            "karte_detail",
            "notes",
        ]
        widgets = {
            "class_date": forms.DateInput(attrs={"type": "date"}),
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time":   forms.TimeInput(attrs={"type": "time"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 科目と生徒の組み合わせが分かれば教材候補を絞り込む
        subject = self.instance.subject if self.instance else None
        student = None
        if self.instance and hasattr(self.instance, 'student_id'):
            try:
                student = self.instance.student
            except StudentProfile.DoesNotExist:
                student = None

        if subject and student:
            # 生徒が過去に使った教材（科目付き）を取得
            used_materials = TeachingMaterial.objects.filter(
                id__in=MaterialUsage.objects.filter(student=student).values_list('material_id', flat=True),
                subject=subject
            )

            # まだ使っていない同科目の教材
            unused_materials = TeachingMaterial.objects.filter(subject=subject).exclude(id__in=used_materials)

            # 既存利用済みを優先して並べ替える
            combined_qs = list(used_materials) + list(unused_materials)
            self.fields['material'].queryset = TeachingMaterial.objects.filter(id__in=[m.id for m in combined_qs])

        elif subject:
            self.fields['material'].queryset = TeachingMaterial.objects.filter(subject=subject)
        else:
            self.fields['material'].queryset = TeachingMaterial.objects.all()

    def clean(self):
        cleaned = super().clean()
        teacher = cleaned.get("teacher")
        student = cleaned.get("student")
        subject = cleaned.get("subject")
        if teacher and student and subject:
            ass = TeacherStudentAssignment.objects.filter(teacher=teacher, student=student).first()
            if ass and ass.subjects.exists() and (subject not in ass.subjects.all()):
                raise ValidationError("この講師-生徒の担当科目に含まれていない科目です。")
        return cleaned

class TeachingMaterialForm(forms.ModelForm):
    class Meta:
        model = TeachingMaterial
        fields = ["title","subject","grade","publisher","description"]

    def clean_title(self):
        t = self.cleaned_data["title"].strip()
        if TeachingMaterial.objects.filter(title__iexact=t).exists():
            raise forms.ValidationError("同名の教材が登録されています。既存を選択するか、名称を工夫してください。")
        return t
