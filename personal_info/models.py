from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone


TEACHER_GRADE = [
    ("college_1", "大学１年生"),
    ("college_2", "大学２年生"),
    ("college_3", "大学３年生"),
    ("college_4", "大学４年生"),
    ("working_adult", "社会人"),
]

STUDENT_GRADE = [
    ("elementary_1", "小学１年生"),
    ("elementary_2", "小学２年生"),
    ("elementary_3", "小学３年生"),
    ("elementary_4", "小学４年生"),
    ("elementary_5", "小学５年生"),
    ("elementary_6", "小学６年生"),
    ("junior_1", "中学１年生"),
    ("junior_2", "中学２年生"),
    ("junior_3", "中学３年生"),
    ("senior_1", "高校１年生"),
    ("senior_2", "高校２年生"),
    ("senior_3", "高校３年生"),
    ("graduate", "既卒"),
]


class Subject(models.Model):
    """指導科目を表すマスターモデル。"""

    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class RewardCategory(models.Model):
    """講師報酬の区分と単価を管理する。"""

    CATEGORY_CHOICES = [
        ("elementary", "小学生"),
        ("junior", "中学生"),
        ("high", "高校生"),
        ("custom", "金額自由設定"),
    ]
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, unique=True)
    reward_per_class = models.IntegerField(blank=True, null=True, verbose_name="１コマ当たりの報酬額")

    def __str__(self):
        return f"{self.get_category_display()} : ￥{self.reward_per_class or '自由設定'}"


class TeachingMaterial(models.Model):
    """授業で利用する教材の情報。"""

    title = models.CharField(max_length=100, unique=True, verbose_name="教材名")
    subject = models.ForeignKey("Subject", on_delete=models.SET_NULL, null=True, blank=True, verbose_name="関連科目")
    grade = models.CharField(max_length=50, choices=STUDENT_GRADE, blank=True, verbose_name="推奨学年")
    publisher = models.CharField(max_length=100, blank=True, verbose_name="出版社")
    description = models.TextField(blank=True, verbose_name="説明（空欄可）")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="教材情報登録者")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="教材情報登録月日")

    def __str__(self):
        return self.title


class AdminProfile(models.Model):
    """管理者ユーザーの基本情報。"""

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, blank=False)
    gender = models.CharField(max_length=6, choices=[("man", "男性"), ("female", "女性")], blank=False)
    age = models.PositiveIntegerField(validators=[MinValueValidator(18)], blank=False)
    address = models.CharField(max_length=100, blank=False)
    phone = models.CharField(max_length=13, blank=False)
    email = models.CharField(max_length=100, blank=False)

    def __str__(self):
        return self.name


class TeacherProfile(models.Model):
    """講師ユーザーに紐づく詳細プロフィール。"""

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, blank=False)
    gender = models.CharField(max_length=6, choices=[("man", "男性"), ("female", "女性")])
    age = models.PositiveIntegerField(validators=[MinValueValidator(18)], blank=False)
    address = models.CharField(max_length=1000, blank=False)
    phone = models.CharField(max_length=13, blank=False)
    email = models.CharField(max_length=100, blank=False)
    school = models.CharField(max_length=50, blank=True)
    grade = models.CharField(choices=TEACHER_GRADE, blank=False)
    subjects = models.ManyToManyField(Subject, blank=True, related_name="teachers")

    def __str__(self):
        return self.name


class StudentProfile(models.Model):
    """生徒ユーザーに紐づく詳細プロフィール。"""

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, blank=False)
    gender = models.CharField(max_length=6, choices=[("man", "男性"), ("female", "女性")])
    age = models.PositiveIntegerField(validators=[MinValueValidator(6)], blank=False)
    address = models.CharField(max_length=100, blank=False)
    phone = models.CharField(max_length=13, blank=False)
    email = models.CharField(max_length=100, blank=False)
    school = models.CharField(max_length=50, blank=True)
    grade = models.CharField(choices=STUDENT_GRADE, blank=False)
    subjects = models.ManyToManyField(Subject, blank=True)
    reward_category = models.ForeignKey(RewardCategory, on_delete=models.SET_NULL, null=True, verbose_name="報酬区分（講師向け）")
    custom_reward_per_class = models.IntegerField(null=True, blank=True, verbose_name="自由報酬額（１コマ）")
    billing_per_class = models.IntegerField(null=True, blank=True, verbose_name="生徒への請求額（１コマ）")

    def __str__(self):
        return self.name

    def clean(self):
        if self.reward_category and self.reward_category.category == "custom":
            if not self.custom_reward_per_class:
                raise ValidationError("金額自由設定の場合は報酬額の入力が必要です。")


class TeacherStudentAssignment(models.Model):
    """講師と生徒の担当関係および担当科目。"""

    teacher = models.ForeignKey("TeacherProfile", on_delete=models.CASCADE)
    student = models.ForeignKey("StudentProfile", on_delete=models.CASCADE)
    subjects = models.ManyToManyField("Subject", blank=True, related_name="ts_assignments")

    class Meta:
        unique_together = [("teacher", "student")]
        verbose_name = "担当講師割当"
        verbose_name_plural = "担当講師割当"

    def __str__(self):
        t = getattr(self.teacher, "name", str(self.teacher_id))
        s = getattr(self.student, "name", str(self.student_id))
        return f"{t} → {s}"


class ClassSchedule(models.Model):
    """授業の予定および実施状況を保持する。"""

    teacher = models.ForeignKey(
        TeacherProfile, on_delete=models.SET_NULL, null=True, blank=True
    )
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True)
    class_date = models.DateField(verbose_name="授業日", null=True, blank=True)
    start_time = models.TimeField(verbose_name="授業開始時刻", null=True, blank=True)
    end_time = models.TimeField(verbose_name="授業終了時刻", null=True, blank=True)
    notes = models.TextField(blank=True, verbose_name="備考")
    is_held = models.BooleanField(default=False, help_text="実施済")
    is_absent = models.BooleanField(default=False, help_text="欠席")
    is_tardy = models.BooleanField(default=False, help_text="遅刻")
    note = models.TextField(blank=True, default="", help_text="備考/実施メモ")
    STATUS_PENDING = "pending"
    STATUS_SCHEDULED = "scheduled"
    STATUS_DONE = "done"
    STATUS_CHOICES = [
        (STATUS_PENDING, "保留"),
        (STATUS_SCHEDULED, "未実施"),
        (STATUS_DONE, "実施済"),
    ]
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
        verbose_name="状態",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    material = models.ForeignKey(
        TeachingMaterial, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="使用教材"
    )
    karte_summary = models.CharField(max_length=200, blank=True, verbose_name="授業概要")
    karte_detail = models.TextField(blank=True, verbose_name="授業内容詳細")

    class Meta:
        indexes = [
            models.Index(fields=["class_date", "teacher"]),
            models.Index(fields=["class_date", "student"]),
            models.Index(fields=["teacher", "class_date", "start_time"]),
            models.Index(fields=["student", "class_date", "start_time"]),
        ]

    def recompute_status(self, *, force: bool = False):
        time_ok = bool(self.class_date and self.start_time and self.end_time)
        teacher_ok = bool(self.teacher_id)
        try:
            karte_confirmed = bool(self.karte.is_confirmed)
        except Exception:
            karte_confirmed = False

        new_status = self.STATUS_PENDING
        if teacher_ok and time_ok:
            new_status = self.STATUS_SCHEDULED
        if karte_confirmed:
            new_status = self.STATUS_DONE
        if force or new_status != self.status:
            self.status = new_status

    def save(self, *args, **kwargs):
        self.recompute_status()
        super().save(*args, **kwargs)

    def __str__(self):
        teacher_name = getattr(self.teacher, "name", "-")
        subject_name = getattr(self.subject, "name", "-")
        return f"{self.class_date} | {self.student.name} | {subject_name} | {teacher_name}"


class ClassKarte(models.Model):
    """授業カルテ（授業内容報告）を保持するモデル。"""

    schedule = models.OneToOneField(
        ClassSchedule, on_delete=models.CASCADE, related_name="karte", null=True, blank=True
    )
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE)
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True)
    class_date = models.DateField(verbose_name="授業日")
    material = models.ForeignKey(
        TeachingMaterial, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="使用教材"
    )
    material_pages = models.CharField(max_length=50, blank=True, verbose_name="授業ページ")
    karte_summary = models.CharField(max_length=200, verbose_name="授業概要")
    karte_detail = models.TextField(blank=True, verbose_name="授業内容詳細")
    goal = models.CharField(max_length=100, blank=True, verbose_name="目標")
    tardy = models.BooleanField(default=False, verbose_name="遅刻の有無")
    evaluation = models.CharField(
        max_length=20,
        choices=[("more", "もう少し"), ("good", "よくできました"), ("great", "大変よくできました")],
        blank=True,
        verbose_name="評価",
    )
    STATUS_DRAFT = "draft"
    STATUS_SUBMITTED = "submitted"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "下書き"),
        (STATUS_SUBMITTED, "提出済"),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    is_confirmed = models.BooleanField(default=False)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    confirmed_by = models.ForeignKey(
        "TeacherProfile", null=True, blank=True, on_delete=models.SET_NULL, related_name="confirmed_kartes"
    )

    def confirm(self, by=None):
        self.is_confirmed = True
        self.confirmed_at = timezone.now()
        if by:
            self.confirmed_by = by
        self.save(update_fields=["is_confirmed", "confirmed_at", "confirmed_by"])
        sc = self.schedule
        if sc and getattr(sc, "status", None) != ClassSchedule.STATUS_DONE:
            sc.status = ClassSchedule.STATUS_DONE
            sc.save(update_fields=["status"])

    def reopen(self):
        self.is_confirmed = False
        self.confirmed_at = None
        self.confirmed_by = None
        self.save(update_fields=["is_confirmed", "confirmed_at", "confirmed_by"])
        sc = self.schedule
        if sc and getattr(sc, "status", None) != ClassSchedule.STATUS_SCHEDULED:
            sc.status = ClassSchedule.STATUS_SCHEDULED
            sc.save(update_fields=["status"])

    def __str__(self):
        return f"{self.class_date} | {self.student.name} | {self.subject} | {self.teacher.name}"

class MaterialUsage(models.Model):
    """生徒ごとの教材利用履歴。"""

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    material = models.ForeignKey(TeachingMaterial, on_delete=models.CASCADE)
    used_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student} - {self.material}"


class DownloadLog(models.Model):
    """帳票ダウンロード等の操作を記録するログ。"""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    student = models.ForeignKey(StudentProfile, on_delete=models.SET_NULL, null=True, blank=True)
    kind = models.CharField(max_length=50)
    count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.kind} by {self.user}"


class AccessLog(models.Model):
    """閲覧経路やレスポンスコードを残すアクセスログ。"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="personal_access_logs",
    )
    path = models.CharField(max_length=255)
    method = models.CharField(max_length=16)
    student = models.ForeignKey("StudentProfile", null=True, blank=True, on_delete=models.SET_NULL)
    teacher = models.ForeignKey("TeacherProfile", null=True, blank=True, on_delete=models.SET_NULL)
    status_code = models.IntegerField(default=200)
    created_at = models.DateTimeField(auto_now_add=True)


class RewardClosing(models.Model):
    """報酬締め処理の実行履歴を表す。"""

    year = models.IntegerField()
    month = models.IntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    closed_at = models.DateTimeField(default=timezone.now)
    closed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        unique_together = ("year", "month")

    def __str__(self):
        return f"{self.year}-{self.month:02d} 締め"


class RewardClosingTeacher(models.Model):
    """締め期間内の講師ごとの報酬集計。"""

    closing = models.ForeignKey(RewardClosing, on_delete=models.CASCADE, related_name="teachers")
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.PROTECT)
    confirmed_count = models.IntegerField()
    unit_reward = models.IntegerField(null=True, blank=True)  # 生徒ごとに異なる場合は None
    total_reward = models.IntegerField()

    def __str__(self):
        return f"{self.closing}: {self.teacher.name} = {self.total_reward}"
