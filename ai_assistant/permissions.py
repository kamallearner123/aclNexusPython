from functools import wraps

from django.core.exceptions import PermissionDenied


def is_pia_system_admin(user):
    if not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True
    return user.roles.filter(name='System Admin').exists()


def pia_system_admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not is_pia_system_admin(request.user):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return _wrapped_view
