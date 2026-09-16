from functools import wraps
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse


def get_lms_user(user):
    """
    Resolves the LMSUser profile for a core.User, creating or syncing if needed.
    """
    if not user.is_authenticated:
        return None

    from .models import LMSUser
    is_admin_user = (
        user.is_superuser or
        user.is_staff or
        user.email in ['admin@admin.com', 'kamal@aptcomputinglabs.com', 'kamalbec2004@gmail.com']
    )
    try:
        lms_user = LMSUser.objects.get(external_user_id=user.id)
        if is_admin_user and lms_user.role not in ['ADMIN', 'MANAGER']:
            lms_user.role = 'ADMIN'
            lms_user.save(update_fields=['role'])
        return lms_user
    except LMSUser.DoesNotExist:
        # Determine role based on ERP flags / roles
        role = 'USER'
        if is_admin_user:
            role = 'ADMIN'
        elif hasattr(user, 'roles') and user.roles.filter(name__icontains='Manager').exists():
            role = 'MANAGER'

        return LMSUser.objects.create(
            external_user_id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            role=role,
        )


def lms_role_required(allowed_roles):
    """
    Decorator for views that checks whether the logged-in user has one of the allowed LMS roles.
    Returns HTTP 403 Forbidden on failure.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                login_url = f"{reverse('login')}?next={request.path}"
                return redirect(login_url)

            is_admin_user = (
                request.user.is_superuser or
                request.user.is_staff or
                request.user.email in ['admin@admin.com', 'kamal@aptcomputinglabs.com', 'kamalbec2004@gmail.com']
            )
            # Admins always have full access to management views
            if is_admin_user and ('ADMIN' in allowed_roles or 'MANAGER' in allowed_roles or 'MENTOR' in allowed_roles):
                return view_func(request, *args, **kwargs)

            lms_user = get_lms_user(request.user)
            if not lms_user or lms_user.role not in allowed_roles:
                return HttpResponseForbidden(
                    "<h1>403 Forbidden</h1><p>You do not have the required permissions to access this LMS resource.</p>"
                )

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
