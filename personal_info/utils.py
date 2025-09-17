from datetime import date
from dateutil.relativedelta import relativedelta

def get_teacher_reward(student):
    if student.reward_category and student.reward_category.category == 'custom':
        return student.custom_reward_per_class or 0
    return student.reward_category.reward_per_class if student.reward_category else 0

def get_student_billing(student):
    return student.billing_per_class or 0

def closing_range(year: int, month: int):
    """
    締日25日の請求・報酬期間：
      前月26日 00:00 〜 当月25日 23:59 まで
    例: 2025-08 を指定 → 2025-07-26〜2025-08-25
    """
    current_25 = date(year, month, 25)
    prev_month_26 = (current_25 - relativedelta(months=1)) + relativedelta(days=1)  # 25日→翌日=26日
    start = prev_month_26.replace(day=26)
    end = current_25
    # 例外月（2月など）も上記計算で安全に処理可能
    return (start, end)

def parse_ym(ym: str):
    """ 'YYYY-MM' を (year, month) に。無効なら None """
    try:
        y, m = ym.split("-")
        return int(y), int(m)
    except Exception:
        return None


from datetime import time
from personal_info.models import ClassSchedule
from django.db.models import Q


def has_conflict(class_date, start_time, end_time, teacher_id, student_id, exclude_id=None):
    qs = ClassSchedule.objects.filter(class_date=class_date)
    if exclude_id:
        qs = qs.exclude(id=exclude_id)
    overlap = Q(start_time__lt=end_time) & Q(end_time__gt=start_time)
    qs = qs.filter(overlap & (Q(teacher_id=teacher_id) | Q(student_id=student_id)))
    return qs.exists()