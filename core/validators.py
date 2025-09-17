"""パスワードバリデーション用ユーティリティ"""

import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


def check_complex_password(password: str) -> bool:
    """英大文字・小文字・数字・記号のうち3種類以上を含み10文字以上か判定"""
    if password is None:
        return False
    categories = 0
    if re.search(r"[A-Z]", password):
        categories += 1
    if re.search(r"[a-z]", password):
        categories += 1
    if re.search(r"\d", password):
        categories += 1
    if re.search(r"[!@#$%^&*()_+\-=\[\]{};:\"\\|,.<>\/\?]", password):
        categories += 1
    return len(password) >= 10 and categories >= 3


class ComplexPasswordValidator:
    """パスワードが要件を満たすか検証するバリデータ"""

    def validate(self, password, user=None):
        if not check_complex_password(password or ""):
            raise ValidationError(
                _(
                    "パスワードは10文字以上で、英大文字・小文字・数字・記号のうち3種類以上を含めてください。"
                ),
                code="password_no_complexity",
            )

    def get_help_text(self):
        return _(
            "パスワードは10文字以上で、英大文字・小文字・数字・記号のうち3種類以上を含めてください。"
        )
