from django.shortcuts import redirect
from django.contrib import messages

PMS_PREFIXES = (
    '/dashboard',
    '/projects',
    '/tasks',
    '/issues',
    '/risks',
    '/teams',
    '/pia',
    '/notes',
    '/system-admin',
    '/attachments',
    '/profile',
)

LMS_PREFIXES = (
    '/lms',
)


def has_pms_access(user):
    """
    Checks if a user has Project Management permissions.
    """
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    return user.roles.filter(
        name__in=['Project Manager', 'Architect', 'Developer', 'Tester', 'Customer Engineer', 'Client']
    ).exists()


def has_lms_access(user):
    """
    Checks if a user has LearnHub LMS permissions.
    """
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    from .models import LMSUser
    try:
        lms_user = LMSUser.objects.filter(external_user_id=user.id, is_active=True).first()
        return bool(lms_user and lms_user.role in ['STUDENT', 'MENTOR', 'MANAGER', 'ADMIN'])
    except Exception:
        return False


class DomainAccessMiddleware:
    """
    Strict Domain Isolation Middleware:
    - Prevents LMS users (e.g. students) from accessing Project Management (PMS).
    - Prevents Project Management users (e.g. developers/clients with LMS role 'USER') from accessing LMS.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # Static assets, media files, admin site, auth urls, and root landing page are exempt
        if (
            path.startswith('/static/') or
            path.startswith('/media/') or
            path.startswith('/admin/') or
            path.startswith('/accounts/') or
            path == '/'
        ):
            return self.get_response(request)

        is_pms_route = any(path == prefix or path.startswith(prefix + '/') for prefix in PMS_PREFIXES)
        is_lms_route = path == '/lms' or path.startswith('/lms/')

        def make_redirect(target_name, message_text):
            messages.error(request, message_text)
            from django.urls import reverse
            from django.http import HttpResponse
            target_url = reverse(target_name)
            if request.headers.get('HX-Request'):
                response = HttpResponse(status=200)
                response['HX-Redirect'] = target_url
                return response
            return redirect(target_url)

        if is_pms_route and request.user.is_authenticated:
            if not has_pms_access(request.user):
                if has_lms_access(request.user):
                    return make_redirect(
                        'lms:dashboard',
                        "Access Restricted: Your account is restricted to LearnHub LMS. You do not have permission to access Project Management."
                    )
                else:
                    return make_redirect(
                        'landing_page',
                        "Access Restricted: You do not have permission to access Project Management."
                    )

        elif is_lms_route and request.user.is_authenticated:
            if not has_lms_access(request.user):
                if has_pms_access(request.user):
                    return make_redirect(
                        'dashboard',
                        "Access Restricted: Your account is restricted to Project Management. You do not have permission to access LearnHub LMS."
                    )
                else:
                    return make_redirect(
                        'landing_page',
                        "Access Restricted: You do not have permission to access LearnHub LMS."
                    )

        return self.get_response(request)


def domain_access_context(request):
    """
    Template context processor exposing domain access flags and LMS context.
    """
    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return {
            'user_has_pms_access': False,
            'user_has_lms_access': False,
            'is_lms_admin': False,
            'lms_user': None,
        }

    from .models import LMSUser
    lms_user = getattr(request, '_cached_lms_user', None)
    if lms_user is None:
        try:
            lms_user = LMSUser.objects.filter(external_user_id=request.user.id, is_active=True).first()
            request._cached_lms_user = lms_user
        except Exception:
            lms_user = None

    is_lms_admin = request.user.is_staff or request.user.is_superuser or bool(lms_user and lms_user.role in ['ADMIN', 'MANAGER'])
    is_lms_mentor = is_lms_admin or bool(lms_user and (lms_user.role in ['INSTRUCTOR', 'MENTOR'] or lms_user.mentor_batches.filter(is_active=True).exists()))

    total_unread_chat_count = 0
    if is_lms_mentor or is_lms_admin:
        try:
            from .models import MentorMessage
            if is_lms_admin:
                total_unread_chat_count = MentorMessage.objects.filter(is_active=True, is_read=False).exclude(sender=lms_user).count() if lms_user else MentorMessage.objects.filter(is_active=True, is_read=False).count()
            elif lms_user:
                mentor_batches_ids = list(lms_user.mentor_batches.filter(is_active=True).values_list('id', flat=True))
                from django.db.models import Q
                total_unread_chat_count = MentorMessage.objects.filter(
                    Q(mentor=lms_user) | Q(batch_id__in=mentor_batches_ids) | Q(student__student_batches__in=mentor_batches_ids),
                    is_active=True,
                    is_read=False
                ).exclude(sender=lms_user).distinct().count()
        except Exception:
            total_unread_chat_count = 0

    return {
        'user_has_pms_access': has_pms_access(request.user),
        'user_has_lms_access': has_lms_access(request.user),
        'is_lms_admin': is_lms_admin,
        'is_lms_mentor': is_lms_mentor,
        'total_unread_chat_count': total_unread_chat_count,
        'lms_user': lms_user,
    }
