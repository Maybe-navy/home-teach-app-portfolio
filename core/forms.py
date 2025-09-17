from django import forms
from django.contrib.auth.password_validation import validate_password
from .validators import check_complex_password


class LoginForm(forms.Form):
    username = forms.CharField(label='ユーザー名', max_length=10)
    password = forms.CharField(label='パスワード', widget=forms.PasswordInput)


class PasswordChangeForm(forms.Form):
    new_password = forms.CharField(label='新しいパスワード', widget=forms.PasswordInput)
    confirm_password = forms.CharField(label='パスワード確認', widget=forms.PasswordInput)

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean(self):
        cleaned_data = super().clean()
        pw1 = cleaned_data.get("new_password")
        pw2 = cleaned_data.get("confirm_password")
        if pw1 and pw2 and pw1 != pw2:
            raise forms.ValidationError("パスワードが一致しません。")
        if pw1:
            if not check_complex_password(pw1):
                raise forms.ValidationError(
                    "パスワードは10文字以上で、英大文字・小文字・数字・記号のうち3種類以上を含めてください。"
                )
            validate_password(pw1, self.user)

        return cleaned_data

