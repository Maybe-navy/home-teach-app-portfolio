from django import forms
from django.contrib.auth.models import User
from core.models import UserProfile
from personal_info.models import (
    TeacherProfile,
    StudentProfile,
    STUDENT_GRADE,
    TEACHER_GRADE,
    Subject,
    RewardCategory,
    ClassSchedule,
)
from core.utils import generate_user_id, generate_compliant_password
from django.db import transaction

class TeacherRegistForm(forms.ModelForm):
    name = forms.CharField(label='講師氏名', max_length=100)
    gender = forms.ChoiceField(label='性別', choices=[('man', '男性'), ('female', '女性')])
    age = forms.IntegerField(label='年齢')
    address = forms.CharField(label='住所', max_length=1000)
    phone = forms.CharField(label='電話番号', max_length=13)
    email = forms.EmailField(label='メールアドレス')
    school = forms.CharField(label='在籍大学名', max_length=50)
    grade = forms.ChoiceField(label='学年', choices=TEACHER_GRADE)
    subjects = forms.ModelMultipleChoiceField(
        label='指導可能科目',
        queryset=Subject.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = TeacherProfile
        fields = ['name', 'gender', 'age', 'address', 'phone', 'email', 'school', 'grade', 'subjects']

    @transaction.atomic
    def save(self, commit=True):
        # ランダムなユーザーIDを発行する
        username = generate_user_id("T")
        raw_password = generate_compliant_password(12)

        # 認証ユーザーと関連する UserProfile を作成
        user = User.objects.create_user(username=username, password=raw_password)
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.user_type = "teacher"
        profile.is_temporary_password = True
        profile.failed_login_attempts = 0
        profile.is_locked = False
        profile.save(update_fields=[
            "user_type",
            "is_temporary_password",
            "failed_login_attempts",
            "is_locked",
        ])

        # TeacherProfile 本体を保存
        teacher = super().save(commit=False)
        teacher.user = user
        if commit:
            teacher.save()
            self.save_m2m()  # subjects の ManyToMany 関係を保存
        return user, raw_password

class StudentRegistForm(forms.ModelForm):
    name = forms.CharField(label='生徒氏名', max_length=100)
    gender = forms.ChoiceField(label='性別', choices=[('man', '男性'), ('female', '女性')])
    age = forms.IntegerField(label='年齢')
    address = forms.CharField(label='住所', max_length=1000)
    phone = forms.CharField(label='電話番号', max_length=13)
    email = forms.EmailField(label='メールアドレス')
    school = forms.CharField(label='在籍校名', max_length=50)
    grade = forms.ChoiceField(label='学年', choices=STUDENT_GRADE)
    subjects = forms.ModelMultipleChoiceField(
        label='希望科目',
        queryset=Subject.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    
    class Meta:
        model = StudentProfile
        fields = ['name', 'gender', 'age', 'address', 'phone', 'email', 'school', 'grade', 'subjects']

    @transaction.atomic
    def save(self, commit=True):
        username = generate_user_id("S")
        raw_password = generate_compliant_password(12)

        user = User.objects.create_user(username=username, password=raw_password)
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.user_type = "student"
        profile.is_temporary_password = True
        profile.failed_login_attempts = 0
        profile.is_locked = False
        profile.save(update_fields=[
            "user_type",
            "is_temporary_password",
            "failed_login_attempts",
            "is_locked",
        ])

        student = super().save(commit=False)
        student.user = user
        if commit:
            student.save()
            self.save_m2m()  # subjects の ManyToMany 関係を保存
        return user, raw_password
    
class ScheduleSearchForm(forms.Form):
    class_date = forms.DateField(label='授業日', required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    teacher_name = forms.CharField(label='講師名', required=False)
    student_name = forms.CharField(label='生徒名', required=False)

class RewardCategoryForm(forms.ModelForm):
    class Meta:
        model = RewardCategory
        fields = ['category', 'reward_per_class']  # カテゴリ値は表示のみ
        widgets = {
            'reward_per_class': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # カテゴリ種別は変更不可のためフォームからの更新を禁止
        self.fields['category'].disabled = True
        # 表示を Bootstrap に合わせる
        self.fields['category'].widget.attrs.update({'class': 'form-select'})

    def clean_reward_per_class(self):
        v = self.cleaned_data.get('reward_per_class')
        # 任意：0や負値を禁止したい場合は以下を有効化
        # if v is not None and v <= 0:
        #     raise forms.ValidationError('0より大きい値を入力してください。')
        return v

class StudentRewardForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = ['billing_per_class', 'reward_category', 'custom_reward_per_class']
        widgets = {
            'billing_per_class': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'reward_category': forms.Select(attrs={'class': 'form-select'}),
            'custom_reward_per_class': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
        }
        help_texts = {
            'custom_reward_per_class': '報酬区分が「金額自由設定」の場合に入力してください。'
        }
    def clean(self):
        cleaned = super().clean()
        rc = cleaned.get('reward_category')
        custom = cleaned.get('custom_reward_per_class')
        if rc and rc.category == 'custom' and not custom:
            self.add_error('custom_reward_per_class', '金額自由設定を選んだ場合は必須です。')
        return cleaned


class ClassScheduleForm(forms.ModelForm):
    """授業情報の登録・編集で使用するフォーム"""

    class_date = forms.DateField(
        label="授業日",
        widget=forms.DateInput(attrs={"type": "date"}),
        required=False,
    )
    start_time = forms.TimeField(
        label="授業開始時刻",
        widget=forms.TimeInput(attrs={"type": "time"}),
        required=False,
    )
    end_time = forms.TimeField(
        label="授業終了時刻",
        widget=forms.TimeInput(attrs={"type": "time"}),
        required=False,
    )

    class Meta:
        model = ClassSchedule
        fields = ["student", "teacher", "subject", "class_date", "start_time", "end_time"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # teacher は必須入力ではないためここで設定
        self.fields["teacher"].required = False
    
class RewardCategoryCreateForm(forms.ModelForm):
    class Meta:
        model = RewardCategory
        fields = ['category', 'reward_per_class']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 既に作成済みのカテゴリを除外して選択肢に出す
        created = set(RewardCategory.objects.values_list('category', flat=True))
        # モデル側の choices を利用
        base_choices = RewardCategory._meta.get_field('category').choices or []
        remain = [(v, lbl) for v, lbl in base_choices if v not in created]
        self.fields['category'] = forms.ChoiceField(
            choices=remain,
            label='区分',
            required=True,
            widget=forms.Select(attrs={'class': 'form-select'}),
        )
        # 何も残っていない場合はメッセージを表示用に help_text を付与
        if not remain:
            self.fields['category'].help_text = 'すべてのカテゴリが作成済みです。'
        # 報酬額入力欄も Bootstrap のスタイルに合わせる
        self.fields['reward_per_class'].widget = forms.NumberInput(attrs={'class': 'form-control', 'min': '0'})

    def clean(self):
        cleaned = super().clean()
        cat = cleaned.get('category')
        if cat and RewardCategory.objects.filter(category=cat).exists():
            # 競合防止（同時作成など）
            raise forms.ValidationError('このカテゴリは既に作成済みです。')
        return cleaned
    
class AccountStatusSearchForm(forms.Form):
    q = forms.CharField(label='ユーザーID/氏名 検索', required=False)
    only_locked = forms.BooleanField(label='ロック中のみ', required=False, initial=True)
    user_type = forms.ChoiceField(
        label='種別', required=False,
        choices=[('', 'すべて'), ('admin', '管理者'), ('teacher', '講師')]
    )

class TeacherEditForm(forms.ModelForm):
    subjects = forms.ModelMultipleChoiceField(
        label='指導可能科目',
        queryset=Subject.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    class Meta:
        model = TeacherProfile
        fields = ['name', 'gender', 'age', 'address', 'phone', 'email', 'school', 'grade', 'subjects']

class StudentEditForm(forms.ModelForm):
    subjects = forms.ModelMultipleChoiceField(
        label='指導希望科目',
        queryset=Subject.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    class Meta:
        model = StudentProfile
        fields = [
            'name','gender','age','address','phone','email','school','grade','subjects',
            'reward_category','custom_reward_per_class','billing_per_class'
        ]

    def clean(self):
        cleaned = super().clean()
        rc = cleaned.get('reward_category')
        custom = cleaned.get('custom_reward_per_class')
        if rc and rc.category == 'custom' and not custom:
            self.add_error('custom_reward_per_class', '報酬区分が「金額自由設定」の場合は金額の入力が必須です。')
        return cleaned


class AssignmentCreateForm(forms.Form):
    teacher = forms.ModelChoiceField(queryset=TeacherProfile.objects.order_by("name"))
    student = forms.ModelChoiceField(queryset=StudentProfile.objects.order_by("name"))
    subjects = forms.ModelMultipleChoiceField(
        queryset=Subject.objects.order_by("name"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    
class CSVUploadForm(forms.Form):
    file = forms.FileField(label="CSVファイル")
