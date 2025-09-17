from django import forms
from personal_info.models import TeachingMaterial, ClassKarte, ClassSchedule, TeacherProfile

EVALUATION_CHOICES = [
    ("more",  "もう少し"),
    ("good",  "よくできました"),
    ("great", "大変よくできました"),
]

class ClassKarteForm(forms.ModelForm):
    class Meta:
        model = ClassKarte
        # 画面で編集させるフィールドだけ
        fields = [
            "tardy", "evaluation",
            "material", "material_pages",
            "karte_summary", "karte_detail",
            "goal",
        ]
        labels = {
            "tardy": "遅刻の有無",
            "evaluation": "評価",
            "material": "使用教材",
            "material_pages": "授業ページ",
            "karte_summary": "授業概要",
            "karte_detail": "授業詳細",
            "goal": "目標",
        }
        widgets = {
            "tardy": forms.CheckboxInput(),
            "evaluation": forms.RadioSelect(choices=EVALUATION_CHOICES),
            "karte_detail": forms.Textarea(attrs={"rows": 6}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # subject はフォームに出さないので、インスタンス/スケジュールから推定して教材を絞り込み
        subject = None
        if self.instance:
            subject = getattr(self.instance, "subject", None) \
                or getattr(getattr(self.instance, "schedule", None), "subject", None)

        if subject:
            self.fields["material"].queryset = TeachingMaterial.objects.filter(subject=subject)
        else:
            self.fields["material"].queryset = TeachingMaterial.objects.none()

        self.fields["material"].empty_label = "--------"  # プルダウンの空表示

class TeacherScheduleSearchForm(forms.Form):
    class_date = forms.DateField(
        label='授業日',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    student_name = forms.CharField(
        label='生徒名',
        required=False
    )

class TeacherScheduleEditForm(forms.ModelForm):
    teacher = forms.ModelChoiceField(
        queryset=TeacherProfile.objects.order_by("name"),
        required=False,
        label="担当講師",
    )

    class Meta:
        model = ClassSchedule
        fields = ["teacher", "class_date", "start_time", "end_time", "notes"]
        widgets = {
            "class_date": forms.DateInput(attrs={"type": "date"}),
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
        }

    def clean(self):
        c = super().clean()
        if c.get("start_time") and c.get("end_time") and c["start_time"] >= c["end_time"]:
            self.add_error("end_time", "終了時刻は開始時刻より後にしてください。")
        return c