from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag
def is_demo() -> bool:
    return bool(getattr(settings, "DEMO_READ_ONLY", False))

