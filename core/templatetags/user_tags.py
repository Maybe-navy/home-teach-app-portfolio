from django import template

register = template.Library()

@register.filter
def display_name(user):
    """ユーザーのプロフィール名を返す。なければユーザーID。"""
    if not getattr(user, 'is_authenticated', False):
        return ''
    for attr in ('teacherprofile', 'studentprofile', 'adminprofile'):
        prof = getattr(user, attr, None)
        name = getattr(prof, 'name', None)
        if name:
            return name
    return getattr(user, 'username', '')
