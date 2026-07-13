from django import template

from ai_assistant.permissions import is_pia_system_admin


register = template.Library()


@register.filter
def is_pia_system_admin_user(user):
    return is_pia_system_admin(user)
