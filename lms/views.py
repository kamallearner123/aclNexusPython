import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.http import JsonResponse, HttpResponseForbidden
from django.utils import timezone
from django.db.models import Count, Q

from .models import (
    LMSUser,
    Course,
    Module,
    Lesson,
    Enrollment,
    LessonProgress,
    LiveClass,
    Assignment,
    AssignmentSubmission,
    CourseCommandMessage,
    CourseInstructor,
    Batch,
    BatchSession,
    BatchMaterial,
    StudentPayment,
    CourseFeedback,
    BatchAssignment,
    SessionAttendance,
    BatchAssignmentAssessment,
    MentorMessage,
)
from .decorators import lms_role_required, get_lms_user
from .services import (
    calculate_course_progress,
    mark_lesson_completed,
    submit_assignment,
    grade_submission,
    publish_command_message,
    sync_batch_course_and_enrollments,
    import_course_materials_from_path,
)
from .selectors import (
    get_next_two_sessions,
    get_active_command_message,
    get_course_mentors,
    get_user_enrollments,
    get_student_assignments,
    get_dashboard_aggregates,
    get_admin_dashboard_data,
    get_batch_detail,
    get_student_payment_data,
)
from .forms import (
    ProfileEditForm,
    PasswordUpdateForm,
    AssignmentSubmissionForm,
    AssignmentGradeForm,
    CourseCommandMessageForm,
    LiveClassForm,
    AssignmentCreateForm,
    CohortUserForm,
    CourseCreateForm,
    BatchForm,
    BatchAssignMembersForm,
    CohortUserEditForm,
    AdminResetPasswordForm,
    StudentPaymentRecordForm,
    StudentPaymentSubmissionForm,
    BatchSessionForm,
    BatchMaterialForm,
    BatchAssignmentForm,
)


@login_required
def dashboard(request):
    """
    Role-aware LMS Dashboard:
    - Administrators & Academic Managers land on the high-level Command & Operations Dashboard
      with full control over Students, Mentors, Batches, Sessions, Materials, and Student Payments.
    - Students land on the Student Learning Dashboard with enrolled courses, batch sessions, and fees.
    - An explicit ?view=learner query allows Admins to view the student perspective.
    """
    lms_user = get_lms_user(request.user)
    is_admin = request.user.is_staff or request.user.is_superuser or (lms_user and lms_user.role in ['ADMIN', 'MANAGER'])
    view_mode = request.GET.get('view')

    if is_admin and view_mode != 'learner' and view_mode != 'mentor':
        admin_data = get_admin_dashboard_data()
        context = {
            'lms_user': lms_user,
            'is_admin': True,
            'course_form': CourseCreateForm(),
            'batch_form': BatchForm(),
            'session_form': BatchSessionForm(),
            'material_form': BatchMaterialForm(),
            'payment_form': StudentPaymentRecordForm(),
            'user_create_form': CohortUserForm(),
            'assign_form': BatchAssignMembersForm(),
            'assignment_form': AssignmentCreateForm(),
            'active_tab': request.GET.get('tab', 'dashboard'),
            **admin_data,
        }
        return render(request, 'lms/admin_dashboard.html', context)

    # Faculty Mentor / Instructor Dashboard Routing
    is_admin = (
        request.user.is_superuser or
        request.user.is_staff or
        request.user.email in ['admin@admin.com', 'kamal@aptcomputinglabs.com', 'kamalbec2004@gmail.com'] or
        (lms_user and lms_user.role in ['ADMIN', 'MANAGER'])
    )
    is_mentor = bool(
        is_admin or
        (lms_user and (lms_user.role in ['INSTRUCTOR', 'MENTOR'] or lms_user.mentor_batches.filter(is_active=True).exists()))
    )
    if (is_mentor or view_mode == 'mentor') and view_mode != 'learner':
        if lms_user and not is_admin:
            assigned = lms_user.mentor_batches.filter(is_active=True).select_related('course').prefetch_related('students', 'sessions')
            if assigned.exists():
                mentor_batches = assigned
            else:
                mentor_batches = Batch.objects.filter(is_active=True).select_related('course').prefetch_related('students', 'sessions')
        else:
            mentor_batches = Batch.objects.filter(is_active=True).select_related('course').prefetch_related('students', 'sessions')

        mentor_students = LMSUser.objects.filter(student_batches__in=mentor_batches, is_active=True).distinct()
        all_sessions = list(BatchSession.objects.filter(
            batch__in=mentor_batches,
            is_active=True,
        ).select_related('batch', 'instructor').prefetch_related('batch__students').order_by('-scheduled_date', '-start_time'))

        session_attendances = list(SessionAttendance.objects.filter(session__batch__in=mentor_batches).select_related('student'))
        
        # Build attendance lookup map: (session_id, student_id) -> status
        session_att_map = {(att.session_id, att.student_id): att.status for att in session_attendances}
        session_notes_map = {(att.session_id, att.student_id): att.notes for att in session_attendances}

        sessions_client_data = []
        for ses in all_sessions:
            ses_atts = [att for att in session_attendances if att.session_id == ses.id]
            ses.present_count = sum(1 for att in ses_atts if att.status == 'PRESENT')
            ses.absent_count = sum(1 for att in ses_atts if att.status == 'ABSENT')
            ses.late_count = sum(1 for att in ses_atts if att.status == 'LATE')
            ses.total_marked = len(ses_atts)
            ses.has_attendance = len(ses_atts) > 0
            
            # Fetch active enrolled students for this session's batch
            batch_students = list(ses.batch.students.filter(is_active=True).order_by('first_name', 'last_name', 'email'))
            ses.batch_students = batch_students
            ses.total_students = len(batch_students)
            ses.attendance_pct = round((ses.present_count / len(batch_students) * 100)) if batch_students else 0

            # Attach student attendance list to session
            student_list_for_ses = []
            for s in batch_students:
                s_status = session_att_map.get((ses.id, s.id), 'PRESENT')
                s_notes = session_notes_map.get((ses.id, s.id), '')
                student_list_for_ses.append({
                    'id': s.id,
                    'name': s.full_name,
                    'email': s.email,
                    'avatar': s.avatar_url if hasattr(s, 'avatar_url') else f"https://ui-avatars.com/api/?name={s.full_name.replace(' ', '+')}",
                    'status': s_status,
                    'notes': s_notes,
                })
            ses.student_attendance_items = student_list_for_ses

            sessions_client_data.append({
                'id': ses.id,
                'title': ses.title,
                'batch_id': ses.batch_id,
                'batch_code': ses.batch.code,
                'batch_name': ses.batch.name,
                'scheduled_date': ses.scheduled_date.strftime('%Y-%m-%d') if ses.scheduled_date else '',
                'start_time': ses.start_time.strftime('%H:%M') if ses.start_time else '',
                'meeting_link': ses.meeting_link or '',
                'has_attendance': ses.has_attendance,
                'present_count': ses.present_count,
                'absent_count': ses.absent_count,
                'late_count': ses.late_count,
                'total_students': ses.total_students,
                'students': student_list_for_ses,
            })

        mentor_assignments = list(BatchAssignment.objects.filter(
            batch__in=mentor_batches,
            is_active=True
        ).select_related('batch', 'target_student', 'assigned_by').prefetch_related('batch__students').order_by('-created_at')[:30])

        all_assignment_assessments = list(BatchAssignmentAssessment.objects.filter(
            assignment__in=mentor_assignments,
            is_active=True
        ).select_related('assignment', 'student', 'assessed_by'))

        assessment_map = {(att.assignment_id, att.student_id): att for att in all_assignment_assessments}

        student_assignment_reports = []
        now_dt = timezone.now()
        total_expected_submissions = 0
        total_submitted_count = 0
        total_pending_grading_count = 0
        total_graded_count = 0
        total_not_submitted_count = 0
        total_overdue_count = 0

        for ma in mentor_assignments:
            if ma.target_student:
                target_students = [ma.target_student]
            else:
                target_students = list(ma.batch.students.filter(is_active=True).order_by('first_name', 'last_name', 'email'))

            ma_assessments = [att for att in all_assignment_assessments if att.assignment_id == ma.id]
            ma.submissions_count = sum(1 for a in ma_assessments if a.submission_url)
            ma.graded_count = sum(1 for a in ma_assessments if a.score is not None)
            ma.total_students = len(target_students)
            ma.submission_pct = round((ma.submissions_count / ma.total_students * 100)) if ma.total_students else 0

            for st in target_students:
                att = assessment_map.get((ma.id, st.id))
                has_submitted = bool(att and att.submission_url)
                is_graded = bool(att and att.score is not None)
                is_overdue = bool(ma.due_date and ma.due_date < now_dt and not has_submitted)
                avatar_url = st.avatar_url if hasattr(st, 'avatar_url') and st.avatar_url else f"https://ui-avatars.com/api/?name={st.full_name.replace(' ', '+')}"

                total_expected_submissions += 1
                if has_submitted:
                    total_submitted_count += 1
                    if is_graded:
                        total_graded_count += 1
                    else:
                        total_pending_grading_count += 1
                else:
                    total_not_submitted_count += 1
                    if is_overdue:
                        total_overdue_count += 1

                student_assignment_reports.append({
                    'assignment': ma,
                    'assignment_id': ma.id,
                    'assignment_title': ma.title,
                    'batch': ma.batch,
                    'batch_id': ma.batch_id,
                    'batch_code': ma.batch.code,
                    'due_date': ma.due_date,
                    'max_score': ma.max_score,
                    'student': st,
                    'student_id': st.id,
                    'student_name': st.full_name,
                    'student_email': st.email,
                    'student_avatar': avatar_url,
                    'has_submitted': has_submitted,
                    'submission_url': att.submission_url if att else None,
                    'submitted_at': att.updated_at if (att and att.submission_url) else None,
                    'is_graded': is_graded,
                    'score': att.score if att else None,
                    'status': att.status if att else ('OVERDUE' if is_overdue else 'PENDING'),
                    'mentor_feedback': att.mentor_feedback if att else '',
                    'assessed_by': att.assessed_by if att else None,
                    'is_overdue': is_overdue,
                    'assessment_id': att.id if att else None,
                })

        # Mentor Chat Inquiries from Students
        mentor_batch_ids = list(mentor_batches.values_list('id', flat=True))
        if is_admin:
            all_mentor_messages = list(MentorMessage.objects.filter(
                is_active=True
            ).select_related('student', 'mentor', 'sender', 'batch').order_by('-created_at'))
        else:
            all_mentor_messages = list(MentorMessage.objects.filter(
                Q(mentor=lms_user) | Q(batch_id__in=mentor_batch_ids) | Q(student__student_batches__in=mentor_batch_ids),
                is_active=True
            ).distinct().select_related('student', 'mentor', 'sender', 'batch').order_by('-created_at'))

        seen_chat_students = set()
        mentor_chat_threads = []
        all_student_inquiries = []
        total_unread_chat_count = 0

        replied_student_ids = set(m.student_id for m in all_mentor_messages if m.sender_id != m.student_id)

        for msg in all_mentor_messages:
            st = msg.student
            avatar_url = st.avatar_url if hasattr(st, 'avatar_url') and st.avatar_url else f"https://ui-avatars.com/api/?name={st.full_name.replace(' ', '+')}"

            if msg.sender_id == st.id:
                all_student_inquiries.append({
                    'id': msg.id,
                    'student': st,
                    'student_id': st.id,
                    'student_name': st.full_name,
                    'student_email': st.email,
                    'student_avatar': avatar_url,
                    'batch': msg.batch or st.student_batches.filter(is_active=True).first(),
                    'message': msg.message,
                    'created_at': msg.created_at,
                    'is_read': msg.is_read,
                    'has_reply': (st.id in replied_student_ids),
                })

            if st.id not in seen_chat_students:
                seen_chat_students.add(st.id)
                unread_cnt = sum(1 for m in all_mentor_messages if m.student_id == st.id and m.sender_id == st.id and not m.is_read)
                total_unread_chat_count += unread_cnt
                mentor_chat_threads.append({
                    'student': st,
                    'student_id': st.id,
                    'student_name': st.full_name,
                    'student_email': st.email,
                    'student_avatar': avatar_url,
                    'batch': msg.batch or st.student_batches.filter(is_active=True).first(),
                    'latest_message': msg.message,
                    'latest_time': msg.created_at,
                    'unread_count': unread_cnt,
                    'has_reply': (st.id in replied_student_ids),
                })

        context = {
            'lms_user': lms_user,
            'is_mentor': True,
            'is_admin': is_admin,
            'mentor_batches': mentor_batches,
            'mentor_students': mentor_students,
            'all_sessions': all_sessions,
            'upcoming_sessions': [s for s in all_sessions if s.status in ['LIVE', 'UPCOMING']],
            'mentor_assignments': mentor_assignments,
            'student_assignment_reports': student_assignment_reports,
            'assignment_report_stats': {
                'total_assignments': len(mentor_assignments),
                'total_expected': total_expected_submissions,
                'total_submitted': total_submitted_count,
                'total_pending_grading': total_pending_grading_count,
                'total_graded': total_graded_count,
                'total_not_submitted': total_not_submitted_count,
                'total_overdue': total_overdue_count,
            },
            'mentor_chat_threads': mentor_chat_threads,
            'all_student_inquiries': all_student_inquiries,
            'total_unread_chat_count': total_unread_chat_count,
            'total_inquiries_count': len(all_student_inquiries),
            'total_batches_count': mentor_batches.count(),
            'total_students_count': mentor_students.count(),
            'total_sessions_count': len(all_sessions),
            'total_assignments_count': len(mentor_assignments),
            'sessions_client_json': json.dumps(sessions_client_data),
            'session_form': BatchSessionForm(),
        }
        return render(request, 'lms/mentor_dashboard.html', context)

    # Student / Learner View
    if lms_user:
        for b in lms_user.student_batches.filter(is_active=True):
            sync_batch_course_and_enrollments(b)

    aggregates = get_dashboard_aggregates(request.user.id)
    student_batches = list(lms_user.student_batches.filter(is_active=True).select_related('course').prefetch_related('sessions', 'materials')) if lms_user else []
    if lms_user and not student_batches:
        # Connect student to active batch if they are enrolled in the course
        enrolled_course_ids = Enrollment.objects.filter(external_user_id=request.user.id, is_active=True).values_list('course_id', flat=True)
        course_batches = Batch.objects.filter(course_id__in=enrolled_course_ids, is_active=True).select_related('course').prefetch_related('sessions', 'materials')
        for cb in course_batches:
            cb.students.add(lms_user)
            student_batches.append(cb)

    student_sessions = BatchSession.objects.filter(
        batch__in=student_batches,
        is_active=True,
        status__in=['UPCOMING', 'LIVE'],
        scheduled_date__gte=timezone.now().date()
    ).select_related('batch', 'instructor').order_by('scheduled_date', 'start_time')[:5] if student_batches else []

    student_materials = BatchMaterial.objects.filter(
        batch__in=student_batches,
        is_active=True
    ).select_related('batch', 'session').order_by('-created_at')[:6] if student_batches else []

    payment_summary = get_student_payment_data(request.user.id)

    context = {
        'lms_user': lms_user,
        'is_admin': is_admin,
        'student_batches': student_batches,
        'student_sessions': student_sessions,
        'student_materials': student_materials,
        'payment_summary': payment_summary,
        **aggregates,
    }
    return render(request, 'lms/dashboard.html', context)


def course_list(request):
    """
    Course catalog & syllabus view.
    For students: displays courses that are registered by the student (assigned by admin).
    For administrators/mentors: displays full academic course catalog.
    """
    # Proactively ensure all active cohorts reflect their courses and student enrollments
    for b in Batch.objects.filter(is_active=True):
        if not b.course or b.students.exists():
            sync_batch_course_and_enrollments(b)

    courses = Course.objects.filter(status='PUBLISHED', is_active=True).order_by('code')

    user_enrollment_map = {}
    lms_user = None
    is_student = False

    if request.user.is_authenticated:
        lms_user = get_lms_user(request.user)
        enrollments = Enrollment.objects.filter(external_user_id=request.user.id, is_active=True)
        user_enrollment_map = {e.course_id: e for e in enrollments}
        is_student = (lms_user and lms_user.role == 'STUDENT') and not (request.user.is_staff or request.user.is_superuser)

    # For students: strictly display courses they are registered in / assigned to
    if is_student and lms_user:
        enrolled_course_ids = set(user_enrollment_map.keys())
        batch_course_ids = set(
            Batch.objects.filter(students=lms_user, course__isnull=False, is_active=True).values_list('course_id', flat=True)
        )
        registered_course_ids = enrolled_course_ids | batch_course_ids
        courses = courses.filter(id__in=registered_course_ids)

    course_data = []
    for c in courses:
        enr = user_enrollment_map.get(c.id)
        instructors = c.instructors.filter(is_active=True).select_related('instructor')
        course_data.append({
            'course': c,
            'enrollment': enr,
            'instructors': instructors,
            'module_count': c.modules.filter(is_active=True).count(),
            'lesson_count': Lesson.objects.filter(module__course=c, is_active=True).count(),
            'running_batches_count': c.batches.filter(status='ONGOING', is_active=True).count(),
        })

    is_admin = request.user.is_superuser or request.user.is_staff or (lms_user and lms_user.role == 'ADMIN')

    context = {
        'courses': course_data,
        'lms_user': lms_user,
        'is_student': is_student,
        'is_admin': is_admin,
    }
    return render(request, 'lms/course_list.html', context)


@login_required
def course_detail(request, slug):
    """
    Comprehensive Course Hub:
    Displays chapters, running batches, completed batches, feedback/reviews,
    and admin controls for importing course materials from a directory path.
    """
    course = get_object_or_404(Course, slug=slug, is_active=True)
    lms_user = get_lms_user(request.user)
    is_admin = request.user.is_superuser or request.user.is_staff or (lms_user and lms_user.role == 'ADMIN')

    # Ensure enrollment exists or fetch it
    enrollment, _ = Enrollment.objects.get_or_create(
        external_user_id=request.user.id,
        course=course,
        defaults={'status': 'ACTIVE', 'progress_percent': 0}
    )

    modules = course.modules.filter(is_active=True).prefetch_related('lessons').order_by('order', 'id')
    total_chapters = Lesson.objects.filter(module__course=course, is_active=True).count()

    completed_lesson_ids = set(
        LessonProgress.objects.filter(
            enrollment=enrollment,
            completed=True
        ).values_list('lesson_id', flat=True)
    )

    # Batches breakdown: running, completed, upcoming
    running_batches = course.batches.filter(status='ONGOING', is_active=True).prefetch_related('mentors', 'students')
    completed_batches = course.batches.filter(status='COMPLETED', is_active=True).prefetch_related('mentors', 'students')
    upcoming_batches = course.batches.filter(status='UPCOMING', is_active=True).prefetch_related('mentors', 'students')

    # Feedback / Reviews
    feedbacks = course.feedbacks.filter(is_public=True).select_related('user', 'batch')
    feedbacks_count = feedbacks.count()
    if feedbacks_count > 0:
        avg_rating = round(sum(f.rating for f in feedbacks) / feedbacks_count, 1)
    else:
        avg_rating = 5.0

    # User's associated batch for this course (if any)
    user_batch = None
    if lms_user:
        user_batch = course.batches.filter(students=lms_user, is_active=True).first()

    next_two_sessions = get_next_two_sessions(course)
    command_message = get_active_command_message(course)
    mentors = get_course_mentors(course)
    assignments = get_student_assignments(course, request.user.id)

    # First uncompleted lesson or first lesson overall for quick resume
    first_lesson = None
    for m in modules:
        for l in m.lessons.filter(is_active=True):
            if l.id not in completed_lesson_ids and not first_lesson:
                first_lesson = l
                break
        if first_lesson:
            break
    if not first_lesson and modules.exists():
        first_mod = modules.first()
        if first_mod and first_mod.lessons.exists():
            first_lesson = first_mod.lessons.first()

    context = {
        'course': course,
        'enrollment': enrollment,
        'modules': modules,
        'total_chapters': total_chapters,
        'completed_lesson_ids': completed_lesson_ids,
        'running_batches': running_batches,
        'completed_batches': completed_batches,
        'completed_batches_count': completed_batches.count(),
        'upcoming_batches': upcoming_batches,
        'feedbacks': feedbacks,
        'feedbacks_count': feedbacks_count,
        'avg_rating': avg_rating,
        'user_batch': user_batch,
        'next_two_sessions': next_two_sessions,
        'command_message': command_message,
        'mentors': mentors,
        'assignments': assignments,
        'first_lesson': first_lesson,
        'lms_user': lms_user,
        'is_admin': is_admin,
    }
    return render(request, 'lms/course_detail.html', context)


@login_required
def import_course_material_view(request):
    """
    Admin option to specify directory path for importing new or updated course materials.
    """
    lms_user = get_lms_user(request.user)
    is_admin = request.user.is_superuser or request.user.is_staff or (lms_user and lms_user.role == 'ADMIN')
    if not is_admin:
        messages.error(request, "Access restricted to administrators.")
        return redirect('lms:course_list')

    if request.method == 'POST':
        course_id = request.POST.get('course_id')
        directory_path = (request.POST.get('directory_path') or '').strip()
        next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or '/lms/?tab=courses'

        course = get_object_or_404(Course, id=course_id)
        if not directory_path:
            messages.error(request, "Please enter a valid directory path containing course material files.")
            return redirect(next_url)

        res = import_course_materials_from_path(course, directory_path)
        if res.get('success'):
            messages.success(
                request,
                f"Successfully synced material for '{course.title}'! "
                f"Imported/Updated {res.get('lessons_created', 0) + res.get('lessons_updated', 0)} chapters/lessons "
                f"across {res.get('modules_count', 0)} syllabus modules."
            )
        else:
            messages.error(request, f"Failed to import materials: {res.get('error', 'Unknown error')}")

        return redirect(next_url)

    return redirect('lms:course_list')


@login_required
def submit_course_feedback_view(request, slug):
    """
    Allows learners or mentors to submit structured feedback and ratings for a course.
    """
    course = get_object_or_404(Course, slug=slug, is_active=True)
    lms_user = get_lms_user(request.user)
    if not lms_user:
        messages.error(request, "Unable to verify learner profile.")
        return redirect('lms:course_detail', slug=slug)

    if request.method == 'POST':
        try:
            rating = int(request.POST.get('rating', 5))
            rating = max(1, min(5, rating))
        except (ValueError, TypeError):
            rating = 5

        title = (request.POST.get('title') or '').strip()
        comment = (request.POST.get('comment') or '').strip()
        batch_id = request.POST.get('batch_id')
        batch = Batch.objects.filter(id=batch_id).first() if batch_id else course.batches.first()

        if not comment:
            messages.error(request, "Please provide feedback comments.")
            return redirect('lms:course_detail', slug=slug)

        CourseFeedback.objects.create(
            course=course,
            user=lms_user,
            batch=batch,
            rating=rating,
            title=title or f"{rating} Star Review",
            comment=comment,
            is_public=True
        )
        messages.success(request, f"Thank you for your feedback on '{course.title}'!")

    return redirect('lms:course_detail', slug=slug)


def execute_python_code_view(request):
    """
    Executes Python snippets submitted from the interactive lesson reader.
    Captures stdout and stderr in real-time with a strict execution timeout.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'stdout': '', 'stderr': 'Authentication required. Please log in to run code.'}, status=401)

    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    import json
    import sys
    import subprocess

    code = ''
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body)
            code = data.get('code', '')
        except Exception:
            pass
    if not code:
        code = request.POST.get('code', '')

    if not code.strip():
        return JsonResponse({'success': True, 'stdout': '', 'stderr': 'No code provided.'})

    try:
        res = subprocess.run(
            [sys.executable, '-c', code],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return JsonResponse({
            'success': res.returncode == 0,
            'stdout': res.stdout,
            'stderr': res.stderr,
            'exit_code': res.returncode,
        })
    except subprocess.TimeoutExpired:
        return JsonResponse({
            'success': False,
            'stdout': '',
            'stderr': 'Execution timed out (5.0 second safety limit exceeded). Check for infinite loops.',
            'exit_code': -1,
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'stdout': '',
            'stderr': f"Execution error: {str(e)}",
            'exit_code': -1,
        })


@login_required
def lesson_view(request, slug, lesson_id):
    """
    Rich interactive lesson player/reader with syllabus sidebar and completion toggle.
    """
    course = get_object_or_404(Course, slug=slug, is_active=True)
    lesson = get_object_or_404(Lesson, id=lesson_id, module__course=course, is_active=True)
    lms_user = get_lms_user(request.user)

    enrollment, _ = Enrollment.objects.get_or_create(
        external_user_id=request.user.id,
        course=course,
        defaults={'status': 'ACTIVE', 'progress_percent': 0}
    )

    progress = LessonProgress.objects.filter(enrollment=enrollment, lesson=lesson).first()
    is_completed = progress.completed if progress else False

    modules = course.modules.filter(is_active=True).prefetch_related('lessons').order_by('order', 'id')
    completed_lesson_ids = set(
        LessonProgress.objects.filter(
            enrollment=enrollment,
            completed=True
        ).values_list('lesson_id', flat=True)
    )

    # Flatten lessons for prev / next navigation
    all_lessons = []
    for m in modules:
        for l in m.lessons.filter(is_active=True).order_by('order', 'id'):
            all_lessons.append(l)

    current_idx = -1
    for idx, l in enumerate(all_lessons):
        if l.id == lesson.id:
            current_idx = idx
            break

    prev_lesson = all_lessons[current_idx - 1] if current_idx > 0 else None
    next_lesson = all_lessons[current_idx + 1] if 0 <= current_idx < len(all_lessons) - 1 else None

    user_batch = None
    if lms_user:
        user_batch = course.batches.filter(students=lms_user, is_active=True).first()
        if not user_batch:
            user_batch = course.batches.filter(is_active=True).first()

    context = {
        'course': course,
        'lesson': lesson,
        'enrollment': enrollment,
        'is_completed': is_completed,
        'modules': modules,
        'completed_lesson_ids': completed_lesson_ids,
        'prev_lesson': prev_lesson,
        'next_lesson': next_lesson,
        'lms_user': lms_user,
        'user_batch': user_batch,
    }
    return render(request, 'lms/lesson_view.html', context)


@login_required
def lesson_toggle_complete(request, slug, lesson_id):
    """
    Action endpoint to mark a lesson completed and recalculate course progress.
    """
    if request.method != 'POST':
        return redirect('lms:lesson_view', slug=slug, lesson_id=lesson_id)

    course = get_object_or_404(Course, slug=slug, is_active=True)
    lesson = get_object_or_404(Lesson, id=lesson_id, module__course=course, is_active=True)
    enrollment = get_object_or_404(Enrollment, external_user_id=request.user.id, course=course)

    _, new_percent = mark_lesson_completed(enrollment, lesson)

    messages.success(request, f"Lesson '{lesson.title}' marked as completed! Course progress: {new_percent}%.")

    next_url = request.POST.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('lms:lesson_view', slug=slug, lesson_id=lesson.id)


@login_required
def live_classes(request):
    """
    Live Classes Schedule:
    Displays all registered batches for the student. Under each batch, displays a table of sessions.
    Ongoing sessions are highlighted in green color.
    Completed sessions display video recording links.
    """
    lms_user = get_lms_user(request.user)
    student_batches = list(lms_user.student_batches.filter(is_active=True).select_related('course').prefetch_related('sessions__instructor')) if lms_user else []

    # If student is enrolled in courses with batches, auto-link them
    if lms_user and not student_batches:
        enrolled_course_ids = Enrollment.objects.filter(external_user_id=request.user.id, is_active=True).values_list('course_id', flat=True)
        course_batches = Batch.objects.filter(course_id__in=enrolled_course_ids, is_active=True).select_related('course').prefetch_related('sessions__instructor')
        for cb in course_batches:
            cb.students.add(lms_user)
            student_batches.append(cb)

    if not student_batches and (request.user.is_staff or request.user.is_superuser or (lms_user and lms_user.role in ['ADMIN', 'MANAGER'])):
        student_batches = list(Batch.objects.filter(is_active=True).select_related('course').prefetch_related('sessions__instructor'))

    now = timezone.now()
    today = now.date()
    current_time = now.time()

    total_sessions_count = 0
    total_ongoing_count = 0

    for b in student_batches:
        batch_sessions = list(b.sessions.filter(is_active=True).select_related('instructor').order_by('scheduled_date', 'start_time'))
        for s in batch_sessions:
            is_ongoing = (s.status == 'LIVE') or (s.scheduled_date == today and s.start_time <= current_time and (not s.end_time or current_time <= s.end_time))
            is_done = (s.status == 'COMPLETED') or (s.scheduled_date < today) or (s.scheduled_date == today and s.end_time and current_time > s.end_time)
            s.is_ongoing = is_ongoing
            s.is_done = is_done
            if is_ongoing:
                total_ongoing_count += 1
            total_sessions_count += 1
        b.batch_sessions = batch_sessions

    active_broadcasts = []
    for b in student_batches:
        if b.course:
            cmd = get_active_command_message(b.course)
            if cmd and cmd not in active_broadcasts:
                active_broadcasts.append(cmd)

    context = {
        'student_batches': student_batches,
        'total_sessions_count': total_sessions_count,
        'total_ongoing_count': total_ongoing_count,
        'active_broadcasts': active_broadcasts,
        'lms_user': lms_user,
    }
    return render(request, 'lms/live_classes.html', context)


@login_required
def assignments_list(request):
    """
    Student assignments dashboard:
    - Shows all registered batches of the student.
    - Under each batch, displays the list of assignments assigned by the teacher (BatchAssignment).
    - Shows due date, submission status, score, mentor feedback, starter code / GitHub links.
    - Allows students to submit or update their solution URL.
    """
    lms_user = get_lms_user(request.user)
    student_batches = list(lms_user.student_batches.filter(is_active=True).select_related('course').prefetch_related('students')) if lms_user else []
    if lms_user and not student_batches:
        enrolled_course_ids = Enrollment.objects.filter(external_user_id=request.user.id, is_active=True).values_list('course_id', flat=True)
        course_batches = Batch.objects.filter(course_id__in=enrolled_course_ids, is_active=True).select_related('course').prefetch_related('students')
        for cb in course_batches:
            cb.students.add(lms_user)
            student_batches.append(cb)

    if not student_batches and (request.user.is_staff or request.user.is_superuser or (lms_user and lms_user.role in ['ADMIN', 'MANAGER'])):
        student_batches = list(Batch.objects.filter(is_active=True).select_related('course').prefetch_related('students'))

    now = timezone.now()
    batch_assignment_sections = []
    total_assigned_count = 0
    total_submitted_count = 0
    total_graded_count = 0

    for b in student_batches:
        b_assignments = list(BatchAssignment.objects.filter(
            batch=b,
            is_active=True,
            status='ACTIVE'
        ).filter(
            Q(target_student__isnull=True) | Q(target_student=lms_user)
        ).select_related('assigned_by', 'batch').order_by('due_date', '-created_at'))

        assessments_map = {}
        if lms_user and b_assignments:
            for att in BatchAssignmentAssessment.objects.filter(
                assignment__in=b_assignments,
                student=lms_user
            ).select_related('assessed_by'):
                assessments_map[att.assignment_id] = att

        assignment_items = []
        for a in b_assignments:
            total_assigned_count += 1
            assessment = assessments_map.get(a.id)
            has_submitted = bool(assessment and assessment.submission_url)
            is_graded = bool(assessment and assessment.score is not None)
            if has_submitted:
                total_submitted_count += 1
            if is_graded:
                total_graded_count += 1

            is_overdue = bool(a.due_date and a.due_date < now and not has_submitted)

            assignment_items.append({
                'assignment': a,
                'assessment': assessment,
                'has_submitted': has_submitted,
                'is_graded': is_graded,
                'is_overdue': is_overdue,
            })

        batch_assignment_sections.append({
            'batch': b,
            'assignments': assignment_items,
            'total_count': len(assignment_items),
        })

    # Legacy / curriculum milestones for enrolled courses
    enrollments = get_user_enrollments(request.user.id)
    enrolled_courses = [e.course for e in enrollments]
    curriculum_assignments = Assignment.objects.filter(
        course__in=enrolled_courses,
        status='ACTIVE',
        is_active=True
    ).select_related('course').order_by('due_date')

    submissions_map = {
        s.assignment_id: s
        for s in AssignmentSubmission.objects.filter(
            external_user_id=request.user.id,
            is_active=True
        )
    }

    assignment_cards = []
    for a in curriculum_assignments:
        sub = submissions_map.get(a.id)
        assignment_cards.append({
            'assignment': a,
            'submission': sub,
        })

    context = {
        'batch_assignment_sections': batch_assignment_sections,
        'assignment_cards': assignment_cards,
        'total_assigned_count': total_assigned_count,
        'total_submitted_count': total_submitted_count,
        'total_graded_count': total_graded_count,
        'lms_user': lms_user,
    }
    return render(request, 'lms/assignments.html', context)


@login_required
def assignment_detail(request, assignment_id):
    """
    Assignment submission details and verification modal/form.
    """
    assignment = get_object_or_404(Assignment, id=assignment_id, is_active=True)
    lms_user = get_lms_user(request.user)
    submission = AssignmentSubmission.objects.filter(
        assignment=assignment,
        external_user_id=request.user.id
    ).first()

    form = AssignmentSubmissionForm(instance=submission)

    context = {
        'assignment': assignment,
        'submission': submission,
        'form': form,
        'lms_user': lms_user,
    }
    return render(request, 'lms/assignment_detail.html', context)


@login_required
def assignment_submit(request, assignment_id):
    """
    POST endpoint for submitting or updating an assignment solution.
    """
    if request.method != 'POST':
        return redirect('lms:assignment_detail', assignment_id=assignment_id)

    assignment = get_object_or_404(Assignment, id=assignment_id, is_active=True)
    submission = AssignmentSubmission.objects.filter(
        assignment=assignment,
        external_user_id=request.user.id
    ).first()

    form = AssignmentSubmissionForm(request.POST, instance=submission)
    if form.is_valid():
        submit_assignment(
            assignment=assignment,
            external_user_id=request.user.id,
            submission_url=form.cleaned_data['submission_url'],
            submission_text=form.cleaned_data['submission_text']
        )
        messages.success(request, f"Assignment '{assignment.title}' successfully submitted for mentor review!")
    else:
        messages.error(request, "Please enter a valid submission URL.")

    return redirect('lms:assignment_detail', assignment_id=assignment_id)


@login_required
def assignment_grade(request, submission_id):
    """
    Mentor/Admin grading endpoint.
    """
    submission = get_object_or_404(AssignmentSubmission, id=submission_id)
    lms_user = get_lms_user(request.user)

    if lms_user.role not in ['ADMIN', 'MANAGER', 'MENTOR'] and not request.user.is_superuser:
        return HttpResponseForbidden("You do not have permission to grade submissions.")

    if request.method == 'POST':
        form = AssignmentGradeForm(request.POST)
        if form.is_valid():
            score = form.cleaned_data['grade_score']
            feedback = form.cleaned_data['mentor_feedback']
            grade_submission(submission, score, feedback)
            messages.success(request, f"Grade and feedback saved for {submission.assignment.title}.")
        else:
            messages.error(request, "Invalid grading data provided.")

    return redirect('lms:admin_hub')


@login_required
def submit_batch_assignment_view(request, assignment_id):
    """
    Endpoint for students to submit their solution (GitHub URL, live demo, Colab) to a BatchAssignment.
    """
    if request.method != 'POST':
        return redirect('lms:assignments_list')

    lms_user = get_lms_user(request.user)
    if not lms_user:
        messages.error(request, "Student account profile not found.")
        return redirect('lms:assignments_list')

    assignment = get_object_or_404(BatchAssignment, id=assignment_id, is_active=True)
    submission_url = request.POST.get('submission_url', '').strip()
    student_notes = request.POST.get('student_notes', '').strip()

    if not submission_url:
        messages.error(request, "Please provide a valid submission URL (e.g. GitHub repository or project link).")
        return redirect('lms:assignments_list')

    assessment, created = BatchAssignmentAssessment.objects.get_or_create(
        assignment=assignment,
        student=lms_user,
        defaults={
            'max_score': assignment.max_score,
            'status': 'PENDING',
            'submission_url': submission_url,
            'mentor_feedback': f"(Student Note: {student_notes})" if student_notes else '',
        }
    )
    if not created:
        assessment.submission_url = submission_url
        assessment.status = 'PENDING'
        if student_notes:
            prev_fb = assessment.mentor_feedback or ''
            if "(Student Note:" in prev_fb:
                assessment.mentor_feedback = f"(Student Note: {student_notes})"
            else:
                assessment.mentor_feedback = f"{prev_fb}\n(Student Note: {student_notes})".strip()
        assessment.save()

    messages.success(request, f"Your solution for '{assignment.title}' was submitted successfully to your faculty instructor.")
    return redirect('lms:assignments_list')


@login_required
def mentors_list(request):
    """
    Faculty mentoring directory with direct chatting and doubt desks.
    """
    lms_user = get_lms_user(request.user)
    mentors = LMSUser.objects.filter(
        role__in=['MENTOR', 'MANAGER', 'ADMIN'],
        is_active=True
    ).prefetch_related('teaching_courses__course').order_by('first_name', 'last_name')

    unread_counts = {}
    if lms_user:
        for m in mentors:
            cnt = MentorMessage.objects.filter(
                student=lms_user,
                mentor=m,
                sender=m,
                is_read=False,
                is_active=True
            ).count()
            if cnt > 0:
                unread_counts[m.id] = cnt

    mentor_cards = []
    for m in mentors:
        courses = [ci.course for ci in m.teaching_courses.filter(is_active=True)]
        mentor_cards.append({
            'mentor': m,
            'courses': courses,
            'unread_count': unread_counts.get(m.id, 0),
        })

    context = {
        'mentor_cards': mentor_cards,
        'lms_user': lms_user,
    }
    return render(request, 'lms/mentors.html', context)


@login_required
def mentor_chat_api(request, mentor_id):
    """
    Chat endpoint between student and faculty mentor:
    - GET: returns list of messages between request.user (student) and mentor_id. Marks incoming unread messages as read.
    - POST: sends a new question/message from student to mentor.
    """
    lms_user = get_lms_user(request.user)
    if not lms_user:
        return JsonResponse({'status': 'error', 'message': 'User profile not found'}, status=403)

    mentor = get_object_or_404(LMSUser, id=mentor_id, is_active=True)

    if request.method == 'POST':
        msg_text = request.POST.get('message', '').strip()
        if not msg_text and request.content_type == 'application/json':
            try:
                import json as _json
                data = _json.loads(request.body.decode('utf-8'))
                msg_text = data.get('message', '').strip()
            except Exception:
                pass

        if not msg_text:
            return JsonResponse({'status': 'error', 'message': 'Message text cannot be empty'}, status=400)

        batch = lms_user.student_batches.filter(mentors=mentor, is_active=True).first()
        if not batch:
            batch = lms_user.student_batches.filter(is_active=True).first()

        new_msg = MentorMessage.objects.create(
            student=lms_user,
            mentor=mentor,
            sender=lms_user,
            batch=batch,
            message=msg_text,
            is_read=False,
        )

        return JsonResponse({
            'status': 'success',
            'message': {
                'id': new_msg.id,
                'sender_id': new_msg.sender_id,
                'sender_name': new_msg.sender.full_name,
                'is_me': True,
                'message': new_msg.message,
                'created_at': new_msg.created_at.strftime('%b %d, %I:%M %p'),
            }
        })

    # GET: fetch messages
    messages_qs = MentorMessage.objects.filter(
        student=lms_user,
        mentor=mentor,
        is_active=True,
    ).select_related('sender').order_by('created_at')

    # Mark unread messages sent by mentor as read
    messages_qs.filter(sender=mentor, is_read=False).update(is_read=True)

    messages_list = []
    for m in messages_qs:
        messages_list.append({
            'id': m.id,
            'sender_id': m.sender_id,
            'sender_name': m.sender.full_name,
            'is_me': (m.sender_id == lms_user.id),
            'message': m.message,
            'created_at': m.created_at.strftime('%b %d, %I:%M %p'),
            'is_read': m.is_read,
        })

    avatar_url = mentor.avatar_url if hasattr(mentor, 'avatar_url') and mentor.avatar_url else f"https://ui-avatars.com/api/?name={mentor.full_name.replace(' ', '+')}"

    return JsonResponse({
        'status': 'success',
        'mentor': {
            'id': mentor.id,
            'name': mentor.full_name,
            'avatar': avatar_url,
            'role': mentor.get_role_display(),
            'specialization': getattr(mentor, 'specialization', '') or 'Faculty Mentor',
            'email': mentor.email,
        },
        'messages': messages_list,
    })


@login_required
def mentor_reply_chat_api(request, student_id):
    """
    Chat endpoint for mentor/teacher to read and reply to student messages:
    - GET: returns full conversation with student_id and marks incoming student messages as read.
    - POST: mentor sends reply to student.
    """
    lms_user = get_lms_user(request.user)
    student = get_object_or_404(LMSUser, id=student_id, is_active=True)

    if request.method == 'POST':
        msg_text = request.POST.get('message', '').strip()
        if not msg_text and request.content_type == 'application/json':
            try:
                import json as _json
                data = _json.loads(request.body.decode('utf-8'))
                msg_text = data.get('message', '').strip()
            except Exception:
                pass

        if not msg_text:
            return JsonResponse({'status': 'error', 'message': 'Reply message cannot be empty.'}, status=400)

        batch = student.student_batches.filter(is_active=True).first()

        new_msg = MentorMessage.objects.create(
            student=student,
            mentor=lms_user,
            sender=lms_user,
            batch=batch,
            message=msg_text,
            is_read=False,
        )

        # Mark all prior incoming messages from this student as read
        MentorMessage.objects.filter(student=student, sender=student, is_read=False).update(is_read=True)

        return JsonResponse({
            'status': 'success',
            'message': {
                'id': new_msg.id,
                'sender_id': new_msg.sender_id,
                'sender_name': new_msg.sender.full_name if new_msg.sender else 'Faculty Mentor',
                'is_me': True,
                'message': new_msg.message,
                'created_at': new_msg.created_at.strftime('%b %d, %I:%M %p'),
            }
        })

    # GET: conversation
    is_admin = request.user.is_staff or request.user.is_superuser or (lms_user and lms_user.role in ['ADMIN', 'MANAGER'])
    if is_admin or not MentorMessage.objects.filter(student=student, mentor=lms_user, is_active=True).exists():
        messages_qs = MentorMessage.objects.filter(
            student=student,
            is_active=True,
        ).select_related('sender').order_by('created_at')
    else:
        messages_qs = MentorMessage.objects.filter(
            student=student,
            mentor=lms_user,
            is_active=True,
        ).select_related('sender').order_by('created_at')

    # Mark student messages as read by mentor
    messages_qs.filter(sender=student, is_read=False).update(is_read=True)

    messages_list = []
    for m in messages_qs:
        messages_list.append({
            'id': m.id,
            'sender_id': m.sender_id,
            'sender_name': m.sender.full_name if m.sender else 'Unknown',
            'is_me': bool(lms_user and m.sender_id == lms_user.id),
            'message': m.message,
            'created_at': m.created_at.strftime('%b %d, %I:%M %p'),
        })

    avatar_url = student.avatar_url if hasattr(student, 'avatar_url') and student.avatar_url else f"https://ui-avatars.com/api/?name={student.full_name.replace(' ', '+')}"

    return JsonResponse({
        'status': 'success',
        'student': {
            'id': student.id,
            'name': student.full_name,
            'email': student.email,
            'avatar': avatar_url,
        },
        'messages': messages_list,
    })


@login_required
def teacher_student_chats_view(request):
    """
    Dedicated Students Chat Workspace for Teachers & Faculty Mentors:
    - Lists incoming student questions and doubt inquiries.
    - Provides instant reply drawer / chat stream.
    """
    lms_user = get_lms_user(request.user)
    is_admin = request.user.is_staff or request.user.is_superuser or (lms_user and lms_user.role in ['ADMIN', 'MANAGER'])
    is_mentor = is_admin or bool(
        lms_user and (lms_user.role in ['INSTRUCTOR', 'MENTOR'] or lms_user.mentor_batches.filter(is_active=True).exists())
    )

    if not (is_mentor or is_admin):
        messages.info(request, "Student doubt chat desk is for faculty mentors and instructors.")
        return redirect('lms:mentors_list')

    if lms_user and not is_admin:
        assigned = lms_user.mentor_batches.filter(is_active=True)
        mentor_batches = assigned if assigned.exists() else Batch.objects.filter(is_active=True)
    else:
        mentor_batches = Batch.objects.filter(is_active=True)

    mentor_batch_ids = list(mentor_batches.values_list('id', flat=True))

    if is_admin:
        all_mentor_messages = list(MentorMessage.objects.filter(
            is_active=True
        ).select_related('student', 'mentor', 'sender', 'batch').order_by('-created_at'))
    else:
        all_mentor_messages = list(MentorMessage.objects.filter(
            Q(mentor=lms_user) | Q(batch_id__in=mentor_batch_ids) | Q(student__student_batches__in=mentor_batch_ids),
            is_active=True
        ).distinct().select_related('student', 'mentor', 'sender', 'batch').order_by('-created_at'))

    seen_chat_students = set()
    mentor_chat_threads = []
    all_student_inquiries = []
    total_unread_chat_count = 0

    replied_student_ids = set(m.student_id for m in all_mentor_messages if m.sender_id != m.student_id)

    for msg in all_mentor_messages:
        st = msg.student
        avatar_url = st.avatar_url if hasattr(st, 'avatar_url') and st.avatar_url else f"https://ui-avatars.com/api/?name={st.full_name.replace(' ', '+')}"

        if msg.sender_id == st.id:
            all_student_inquiries.append({
                'id': msg.id,
                'student': st,
                'student_id': st.id,
                'student_name': st.full_name,
                'student_email': st.email,
                'student_avatar': avatar_url,
                'batch': msg.batch or st.student_batches.filter(is_active=True).first(),
                'message': msg.message,
                'created_at': msg.created_at,
                'is_read': msg.is_read,
                'has_reply': (st.id in replied_student_ids),
            })

        if st.id not in seen_chat_students:
            seen_chat_students.add(st.id)
            unread_cnt = sum(1 for m in all_mentor_messages if m.student_id == st.id and m.sender_id == st.id and not m.is_read)
            total_unread_chat_count += unread_cnt
            mentor_chat_threads.append({
                'student': st,
                'student_id': st.id,
                'student_name': st.full_name,
                'student_email': st.email,
                'student_avatar': avatar_url,
                'batch': msg.batch or st.student_batches.filter(is_active=True).first(),
                'latest_message': msg.message,
                'latest_time': msg.created_at,
                'unread_count': unread_cnt,
                'has_reply': (st.id in replied_student_ids),
            })

    active_student_id = request.GET.get('student_id')
    if not active_student_id and mentor_chat_threads:
        active_student_id = mentor_chat_threads[0]['student_id']

    context = {
        'lms_user': lms_user,
        'is_mentor': is_mentor,
        'is_admin': is_admin,
        'mentor_batches': mentor_batches,
        'mentor_chat_threads': mentor_chat_threads,
        'all_student_inquiries': all_student_inquiries,
        'total_unread_chat_count': total_unread_chat_count,
        'total_inquiries_count': len(all_student_inquiries),
        'total_threads_count': len(mentor_chat_threads),
        'active_student_id': active_student_id,
    }
    return render(request, 'lms/teacher_student_chats.html', context)


@login_required
@lms_role_required(allowed_roles=['ADMIN', 'MANAGER', 'MENTOR', 'INSTRUCTOR'])
def mentor_create_assignment_view(request):
    """
    Allows teachers/mentors to assign tasks to all students in a batch or an individual student.
    """
    if request.method == 'POST':
        batch_id = request.POST.get('batch_id')
        batch = get_object_or_404(Batch, pk=batch_id)
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        due_date_raw = request.POST.get('due_date')
        due_date = None
        if due_date_raw:
            try:
                from django.utils.dateparse import parse_datetime
                due_date = parse_datetime(due_date_raw)
                if due_date and timezone.is_naive(due_date):
                    due_date = timezone.make_aware(due_date)
            except Exception:
                due_date = None

        max_score = int(request.POST.get('max_score') or 100)
        resource_url = request.POST.get('resource_url', '').strip() or None
        target_audience = request.POST.get('target_audience', 'ALL')
        target_student_id = request.POST.get('target_student_id')

        target_student = None
        if target_audience == 'INDIVIDUAL' and target_student_id:
            target_student = LMSUser.objects.filter(id=target_student_id, is_active=True).first()

        lms_user = get_lms_user(request.user)
        assignment = BatchAssignment.objects.create(
            batch=batch,
            title=title,
            description=description,
            due_date=due_date,
            max_score=max_score,
            resource_url=resource_url,
            assigned_by=lms_user,
            target_student=target_student,
            status='ACTIVE'
        )
        target_desc = "All Students" if not target_student else target_student.full_name
        messages.success(request, f"Assignment '{assignment.title}' assigned to {target_desc} in batch {batch.code}!")

    return redirect(request.POST.get('next') or 'lms:dashboard')


@login_required
def profile_view(request):
    """
    View and edit LMS profile with optional password update.
    """
    lms_user = get_lms_user(request.user)

    if request.method == 'POST':
        if 'update_profile' in request.POST:
            profile_form = ProfileEditForm(request.POST, instance=lms_user)
            password_form = PasswordUpdateForm(user=request.user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Your profile details have been successfully updated.")
                return redirect('lms:profile')
        elif 'update_password' in request.POST:
            profile_form = ProfileEditForm(instance=lms_user)
            password_form = PasswordUpdateForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                new_password = password_form.cleaned_data['new_password']
                request.user.set_password(new_password)
                request.user.save()
                update_session_auth_hash(request, request.user)
                messages.success(request, "Your password has been changed successfully.")
                return redirect('lms:profile')
        else:
            profile_form = ProfileEditForm(instance=lms_user)
            password_form = PasswordUpdateForm(user=request.user)
    else:
        profile_form = ProfileEditForm(instance=lms_user)
        password_form = PasswordUpdateForm(user=request.user)

    context = {
        'lms_user': lms_user,
        'profile_form': profile_form,
        'password_form': password_form,
    }
    return render(request, 'lms/profile.html', context)


from .selectors import (
    get_next_two_sessions,
    get_active_command_message,
    get_course_mentors,
    get_user_enrollments,
    get_student_assignments,
    get_dashboard_aggregates,
    get_courses_with_stats,
)
from .forms import (
    ProfileEditForm,
    PasswordUpdateForm,
    AssignmentSubmissionForm,
    AssignmentGradeForm,
    CourseCommandMessageForm,
    LiveClassForm,
    AssignmentCreateForm,
    CohortUserForm,
    CourseCreateForm,
    LMSUserCreateForm,
    ModuleCreateForm,
    LessonCreateForm,
)


@login_required
@lms_role_required(allowed_roles=['ADMIN', 'MANAGER', 'MENTOR'])
def admin_hub(request):
    """
    Operational command center for broadcast messages, live class schedules,
    course management, student enrollment / joining, cohort management,
    and deliverable submission reviews.
    """
    lms_user = get_lms_user(request.user)
    courses = Course.objects.filter(is_active=True).order_by('code')
    command_messages = CourseCommandMessage.objects.filter(is_active=True).select_related('course')
    live_sessions = LiveClass.objects.filter(is_active=True).select_related('course', 'instructor').order_by('scheduled_date', 'start_time')
    assignments = Assignment.objects.filter(is_active=True).select_related('course').order_by('course', 'order')
    pending_submissions = AssignmentSubmission.objects.filter(
        status__in=['SUBMITTED', 'REVISION_REQUESTED']
    ).select_related('assignment', 'assignment__course').order_by('-submitted_at')
    cohort_users = LMSUser.objects.filter(is_active=True).order_by('role', 'first_name')
    students = LMSUser.objects.filter(role='STUDENT', is_active=True).order_by('first_name', 'last_name')
    mentors = LMSUser.objects.filter(role__in=['MENTOR', 'MANAGER', 'ADMIN'], is_active=True).order_by('first_name')

    # Comprehensive course operational stats
    courses_stats = get_courses_with_stats()

    # Forms
    course_create_form = CourseCreateForm()
    user_create_form = LMSUserCreateForm()
    command_form = CourseCommandMessageForm()
    live_class_form = LiveClassForm()
    assignment_form = AssignmentCreateForm()
    cohort_user_form = CohortUserForm()
    module_create_form = ModuleCreateForm()
    lesson_create_form = LessonCreateForm()

    # Active tab parameter
    active_tab = request.GET.get('tab', 'courses')

    # Summary metric totals
    total_running_courses = sum(1 for c in courses_stats if c['is_running'])
    total_enrollments = sum(c['total_enrolled'] for c in courses_stats)
    overall_avg_progress = (
        round(sum(c['avg_progress'] for c in courses_stats) / len(courses_stats))
        if courses_stats else 0
    )

    context = {
        'lms_user': lms_user,
        'courses': courses,
        'courses_stats': courses_stats,
        'command_messages': command_messages,
        'live_sessions': live_sessions,
        'assignments': assignments,
        'pending_submissions': pending_submissions,
        'cohort_users': cohort_users,
        'students': students,
        'mentors': mentors,
        'course_create_form': course_create_form,
        'user_create_form': user_create_form,
        'command_form': command_form,
        'live_class_form': live_class_form,
        'assignment_form': assignment_form,
        'cohort_user_form': cohort_user_form,
        'module_create_form': module_create_form,
        'lesson_create_form': lesson_create_form,
        'active_tab': active_tab,
        'total_running_courses': total_running_courses,
        'total_enrollments': total_enrollments,
        'overall_avg_progress': overall_avg_progress,
    }
    return render(request, 'lms/admin_hub.html', context)


@login_required
@lms_role_required(allowed_roles=['ADMIN', 'MANAGER'])
def create_course_view(request):
    """
    Creates a new Course in the LMS, assigns instructors, and optionally
    joins/enrolls all active cohort students immediately.
    """
    if request.method == 'POST':
        form = CourseCreateForm(request.POST)
        if form.is_valid():
            course = form.save(commit=False)
            if not course.thumbnail:
                course.thumbnail = 'genai.svg'
            course.save()

            lead_instructor = form.cleaned_data.get('lead_instructor')
            if lead_instructor:
                CourseInstructor.objects.create(
                    course=course,
                    instructor=lead_instructor,
                    role='LEAD',
                    is_primary=True
                )

            # Auto-join students if requested
            enrolled_count = 0
            if form.cleaned_data.get('enroll_all_students'):
                students = LMSUser.objects.filter(role='STUDENT', is_active=True)
                for student in students:
                    Enrollment.objects.get_or_create(
                        external_user_id=student.external_user_id,
                        course=course,
                        defaults={'status': 'ACTIVE', 'progress_percent': 0}
                    )
                    enrolled_count += 1

            # Seed a starter introductory module and lesson
            module = Module.objects.create(
                course=course,
                title='Module 1: Orientation & Architecture Foundations',
                description='Curriculum overview, environment setup, and architectural principles.',
                order=1
            )
            Lesson.objects.create(
                module=module,
                title='1.1 Course Orientation & Syllabus Walkthrough',
                lesson_type='ARTICLE',
                duration_minutes=15,
                content='Welcome to the course! Review the syllabus milestones, architecture lab expectations, and class schedule.',
                order=1,
                is_required=True
            )

            messages.success(
                request,
                f"Course [{course.code}] '{course.title}' created successfully! "
                f"Assigned lead instructor and joined {enrolled_count} students."
            )
            return redirect(request.POST.get('next', '/lms/?tab=courses'))
        else:
            messages.error(request, "Failed to create course. Please review the errors.")
    return redirect(request.POST.get('next', '/lms/?tab=courses'))


@login_required
@lms_role_required(allowed_roles=['ADMIN', 'MANAGER'])
def join_students_view(request):
    """
    Handles joining (enrolling) or removing students from courses,
    as well as assigning faculty mentors to courses.
    """
    if request.method == 'POST':
        action = request.POST.get('action')
        course_id = request.POST.get('course_id')
        course = get_object_or_404(Course, pk=course_id)

        if action == 'enroll_all':
            students = LMSUser.objects.filter(role='STUDENT', is_active=True)
            count = 0
            for s in students:
                _, created = Enrollment.objects.get_or_create(
                    external_user_id=s.external_user_id,
                    course=course,
                    defaults={'status': 'ACTIVE', 'progress_percent': 0}
                )
                if created:
                    count += 1
            messages.success(request, f"Joined {count} new students to course [{course.code}]. All active cohort students are now enrolled!")

        elif action == 'enroll_single':
            student_id = request.POST.get('student_id')
            student = get_object_or_404(LMSUser, pk=student_id)
            enr, created = Enrollment.objects.get_or_create(
                external_user_id=student.external_user_id,
                course=course,
                defaults={'status': 'ACTIVE', 'progress_percent': 0}
            )
            if created:
                messages.success(request, f"Enrolled {student.full_name} ({student.email}) into [{course.code}] '{course.title}'.")
            else:
                messages.info(request, f"{student.full_name} is already enrolled in [{course.code}].")

        elif action == 'unenroll':
            enrollment_id = request.POST.get('enrollment_id')
            enrollment = get_object_or_404(Enrollment, pk=enrollment_id, course=course)
            student_u = LMSUser.objects.filter(external_user_id=enrollment.external_user_id).first()
            s_name = student_u.full_name if student_u else f"User #{enrollment.external_user_id}"
            enrollment.delete()
            messages.success(request, f"Removed student {s_name} from course [{course.code}].")

        elif action == 'assign_instructor':
            instructor_id = request.POST.get('instructor_id')
            role = request.POST.get('role', 'LEAD')
            instructor = get_object_or_404(LMSUser, pk=instructor_id)
            ci, created = CourseInstructor.objects.update_or_create(
                course=course,
                instructor=instructor,
                defaults={'role': role, 'is_primary': (role == 'LEAD'), 'is_active': True}
            )
            messages.success(request, f"Assigned {instructor.full_name} as {ci.get_role_display()} for [{course.code}].")

        elif action == 'remove_instructor':
            ci_id = request.POST.get('course_instructor_id')
            ci = get_object_or_404(CourseInstructor, pk=ci_id, course=course)
            name = ci.instructor.full_name
            ci.delete()
            messages.success(request, f"Removed instructor {name} from course [{course.code}].")

        else:
            messages.error(request, "Unrecognized enrollment action.")

        return redirect(request.POST.get('next', f'/lms/?tab=courses&course_id={course.id}'))

    return redirect(request.GET.get('next', '/lms/?tab=courses'))


@login_required
@lms_role_required(allowed_roles=['ADMIN', 'MANAGER'])
def add_cohort_user_view(request):
    """
    Creates a new user account across both default DB (for authentication)
    and LMS DB (for LMS identity, role, and curricula access).
    """
    if request.method == 'POST':
        form = LMSUserCreateForm(request.POST)
        if form.is_valid():
            from core.models import User as CoreUser

            email = form.cleaned_data['email'].strip().lower()
            first_name = form.cleaned_data['first_name'].strip()
            last_name = form.cleaned_data['last_name'].strip()
            role = form.cleaned_data['role']
            password = form.cleaned_data.get('password') or 'AclMission@123'
            specialization = form.cleaned_data.get('specialization', '')
            phone = form.cleaned_data.get('phone', '')
            bio = form.cleaned_data.get('bio', '')
            courses_to_enroll = form.cleaned_data.get('courses_to_enroll')

            # 1. Look up or create authentication User in core database
            core_user = CoreUser.objects.filter(email=email).first()
            if not core_user:
                core_user = CoreUser(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    is_active=True,
                    is_staff=(role == 'ADMIN'),
                    is_superuser=(role == 'ADMIN'),
                )
                core_user.set_password(password)
                core_user.save()
            else:
                core_user.first_name = first_name
                core_user.last_name = last_name
                if role == 'ADMIN':
                    core_user.is_staff = True
                if password and form.cleaned_data.get('password'):
                    core_user.set_password(password)
                core_user.save()

            # 2. Create or update LMSUser in LMS database
            lms_user, created = LMSUser.objects.update_or_create(
                external_user_id=core_user.id,
                defaults={
                    'email': email,
                    'first_name': first_name,
                    'last_name': last_name,
                    'role': role,
                    'specialization': specialization,
                    'phone': phone,
                    'bio': bio,
                    'is_active': True,
                }
            )

            # 3. Associate courses
            if courses_to_enroll:
                for c in courses_to_enroll:
                    if role == 'STUDENT':
                        Enrollment.objects.get_or_create(
                            external_user_id=core_user.id,
                            course=c,
                            defaults={'status': 'ACTIVE', 'progress_percent': 0}
                        )
                    elif role in ['MENTOR', 'MANAGER', 'ADMIN']:
                        CourseInstructor.objects.get_or_create(
                            course=c,
                            instructor=lms_user,
                            defaults={'role': 'LEAD', 'is_primary': True, 'is_active': True}
                        )

            role_label = dict(LMSUserCreateForm.ROLE_CHOICES).get(role, role)
            messages.success(
                request,
                f"Successfully added {role_label}: {first_name} {last_name} ({email})! "
                f"Initial login password: {password}"
            )
            return redirect('/lms/admin-hub/?tab=cohort')
        else:
            messages.error(request, "Failed to add user. Please check the form errors.")
    return redirect('/lms/admin-hub/?tab=cohort')


@login_required
@lms_role_required(allowed_roles=['ADMIN', 'MANAGER'])
def add_course_module_view(request):
    """
    Creates a new module for a course from the Admin Hub.
    """
    if request.method == 'POST':
        form = ModuleCreateForm(request.POST)
        if form.is_valid():
            module = form.save()
            messages.success(request, f"Module '{module.title}' added to [{module.course.code}].")
            return redirect(f'/lms/admin-hub/?tab=courses')
        else:
            messages.error(request, "Failed to create module. Please check input fields.")
    return redirect('/lms/admin-hub/?tab=courses')


@login_required
@lms_role_required(allowed_roles=['ADMIN', 'MANAGER'])
def add_course_lesson_view(request):
    """
    Creates a new lesson for a module from the Admin Hub.
    """
    if request.method == 'POST':
        form = LessonCreateForm(request.POST)
        if form.is_valid():
            lesson = form.save()
            messages.success(request, f"Lesson '{lesson.title}' added to {lesson.module.course.code}.")
            return redirect(f'/lms/admin-hub/?tab=courses')
        else:
            messages.error(request, "Failed to create lesson. Please check input fields.")
    return redirect('/lms/admin-hub/?tab=courses')


@login_required
@lms_role_required(allowed_roles=['ADMIN', 'MANAGER', 'MENTOR'])
def create_command_message(request):
    if request.method == 'POST':
        form = CourseCommandMessageForm(request.POST)
        if form.is_valid():
            publish_command_message(
                course=form.cleaned_data['course'],
                title=form.cleaned_data['title'],
                previous_session_summary=form.cleaned_data['previous_session_summary'],
                previous_session_recording_url=form.cleaned_data['previous_session_recording_url'],
                next_class_topic=form.cleaned_data['next_class_topic'],
                next_class_datetime=form.cleaned_data['next_class_datetime'],
                next_class_link=form.cleaned_data['next_class_link'],
                published_by_id=request.user.id
            )
            messages.success(request, "New Course Command Message published and broadcasted!")
        else:
            messages.error(request, "Failed to publish message. Please check the fields.")
    return redirect('/lms/admin-hub/?tab=broadcast')


@login_required
@lms_role_required(allowed_roles=['ADMIN', 'MANAGER', 'MENTOR'])
def schedule_live_class_view(request):
    if request.method == 'POST':
        form = LiveClassForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Live class session scheduled successfully!")
        else:
            messages.error(request, "Failed to schedule live class. Please check inputs.")
    return redirect('/lms/admin-hub/?tab=live')


@login_required
@lms_role_required(allowed_roles=['ADMIN', 'MANAGER', 'MENTOR'])
def create_assignment_view(request):
    if request.method == 'POST':
        form = AssignmentCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Assignment deliverable created!")
        else:
            messages.error(request, "Failed to create assignment.")
    return redirect('/lms/admin-hub/?tab=assignment')


@login_required
@lms_role_required(allowed_roles=['ADMIN', 'MANAGER'])
def manage_cohort_user_view(request):
    if request.method == 'POST':
        form = CohortUserForm(request.POST)
        if form.is_valid():
            user_obj = form.save(commit=False)
            existing = LMSUser.objects.filter(external_user_id=user_obj.external_user_id).first()
            if existing:
                existing.email = user_obj.email
                existing.first_name = user_obj.first_name
                existing.last_name = user_obj.last_name
                existing.role = user_obj.role
                existing.specialization = user_obj.specialization
                existing.phone = user_obj.phone
                existing.bio = user_obj.bio
                existing.save()
                messages.success(request, f"Updated cohort user {existing.email}.")
            else:
                user_obj.save()
                messages.success(request, f"Added cohort user {user_obj.email}.")
        else:
            messages.error(request, "Failed to update cohort user.")
    return redirect('/lms/admin-hub/?tab=cohort')


# =========================================================================================
# BATCHES MANAGEMENT VIEWS
# =========================================================================================

def _generate_batch_sessions(batch):
    """
    Auto-generates upcoming BatchSession entries for repetitive days across the next 4 weeks.
    """
    import re
    from datetime import timedelta, datetime
    schedule_str = f"{batch.schedule_days} {batch.schedule}".lower()
    
    day_map = {
        'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6
    }
    
    target_weekdays = set()
    for key, val in day_map.items():
        if key in schedule_str:
            target_weekdays.add(val)
            
    if not target_weekdays:
        target_weekdays = {0, 2, 4} # Mon, Wed, Fri by default
        
    start_date = batch.start_date or timezone.now().date()
    start_time = None
    end_time = None
    
    if batch.schedule_time:
        parts = re.findall(r'(\d{1,2}:\d{2})', batch.schedule_time)
        if len(parts) >= 1:
            try:
                start_time = datetime.strptime(parts[0], '%H:%M').time()
            except Exception:
                pass
        if len(parts) >= 2:
            try:
                end_time = datetime.strptime(parts[1], '%H:%M').time()
            except Exception:
                pass
                
    if not start_time:
        start_time = datetime.strptime('19:00', '%H:%M').time()
    if not end_time:
        end_time = datetime.strptime('21:00', '%H:%M').time()
        
    session_num = 1
    for day_offset in range(28): # 4 weeks
        cur_date = start_date + timedelta(days=day_offset)
        if cur_date.weekday() in target_weekdays:
            day_name = cur_date.strftime('%A')
            BatchSession.objects.create(
                batch=batch,
                title=f"Class {session_num}: {batch.name} ({day_name})",
                meeting_link=batch.zoom_link,
                scheduled_date=cur_date,
                start_time=start_time,
                end_time=end_time,
                status='UPCOMING',
                agenda=f"Scheduled interactive lecture & hands-on lab. Recurring: {batch.full_schedule}"
            )
            session_num += 1


@login_required
@lms_role_required(allowed_roles=['ADMIN', 'MANAGER'])
def create_batch_view(request):
    is_ajax = (
        request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
        'application/json' in request.headers.get('Accept', '') or
        request.POST.get('ajax') == '1'
    )
    if request.method == 'POST':
        form = BatchForm(request.POST)
        if form.is_valid():
            batch = form.save()
            sync_batch_course_and_enrollments(batch)
            if form.cleaned_data.get('auto_generate_sessions') and (batch.schedule_days or batch.schedule):
                try:
                    _generate_batch_sessions(batch)
                except Exception:
                    pass
            messages.success(request, f"Batch '{batch.name}' ({batch.code}) created successfully!")
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': f"Batch '{batch.name}' ({batch.code}) created successfully!",
                    'batch_id': batch.id,
                    'code': batch.code,
                    'name': batch.name,
                    'redirect_url': '/lms/?tab=batches'
                })
        else:
            errors_dict = {field: [str(e) for e in errs] for field, errs in form.errors.items()}
            err_msg = "; ".join([f"{f}: {', '.join(e)}" for f, e in errors_dict.items()])
            messages.error(request, f"Failed to create batch: {err_msg}")
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'error': err_msg,
                    'errors': errors_dict
                }, status=400)
    return redirect(request.POST.get('next') or '/lms/?tab=batches')


@login_required
@lms_role_required(allowed_roles=['ADMIN', 'MANAGER'])
def edit_batch_view(request, pk):
    batch = get_object_or_404(Batch, pk=pk)
    if request.method == 'POST':
        form = BatchForm(request.POST, instance=batch)
        if form.is_valid():
            form.save()
            messages.success(request, f"Batch '{batch.code}' updated successfully.")
        else:
            messages.error(request, f"Error updating batch: {form.errors.as_text()}")
    return redirect(request.POST.get('next') or '/lms/?tab=batches')


@login_required
@lms_role_required(allowed_roles=['ADMIN', 'MANAGER'])
def delete_batch_view(request, pk):
    batch = get_object_or_404(Batch, pk=pk)
    if request.method == 'POST':
        batch_name = batch.name
        batch.delete()
        messages.success(request, f"Batch '{batch_name}' was removed.")
    return redirect('/lms/?tab=batches')


@login_required
@lms_role_required(allowed_roles=['ADMIN', 'MANAGER'])
def assign_batch_members_view(request, pk):
    batch = get_object_or_404(Batch, pk=pk)
    if request.method == 'POST':
        scope = request.POST.get('scope', 'both')
        mode = request.POST.get('mode', 'sync')

        # 1. Update students if scope covers students
        if scope in ['students', 'both']:
            student_ids = request.POST.getlist('students')
            if mode == 'add':
                if student_ids:
                    batch.students.add(*student_ids)
            else:
                batch.students.set(student_ids)

        # 2. Update mentors if scope covers mentors
        if scope in ['mentors', 'both']:
            mentor_ids = request.POST.getlist('mentors')
            if mode == 'add':
                if mentor_ids:
                    batch.mentors.add(*mentor_ids)
            else:
                batch.mentors.set(mentor_ids)

        # 3. Always guarantee course exists and all batch students are enrolled
        sync_batch_course_and_enrollments(batch)

        messages.success(request, f"Updated members for batch '{batch.code}': {batch.students.count()} students, {batch.mentors.count()} mentors.")
    return redirect(request.POST.get('next') or '/lms/?tab=batches')


@login_required
def batch_detail_view(request, pk):
    detail_data = get_batch_detail(pk)
    if not detail_data:
        messages.error(request, "Batch not found.")
        return redirect('/lms/')

    batch = detail_data['batch']
    lms_user = get_lms_user(request.user)
    is_admin = (
        request.user.is_superuser or
        request.user.is_staff or
        request.user.email in ['admin@admin.com', 'kamal@aptcomputinglabs.com', 'kamalbec2004@gmail.com'] or
        (lms_user and lms_user.role in ['ADMIN', 'MANAGER'])
    )

    # Verify access: admin, assigned mentor/instructor, or enrolled student
    is_mentor = bool(
        is_admin or
        (lms_user and (lms_user.role in ['INSTRUCTOR', 'MENTOR'] or batch.mentors.filter(id=lms_user.id).exists()))
    )
    is_enrolled_in_course = bool(batch.course and Enrollment.objects.filter(external_user_id=request.user.id, course=batch.course, is_active=True).exists())
    is_student = bool(lms_user and (batch.students.filter(id=lms_user.id).exists() or is_enrolled_in_course or lms_user.role == 'STUDENT'))

    if not (is_admin or is_mentor or is_student):
        messages.error(request, "You do not have permission to access this batch.")
        return redirect('/lms/')

    if is_enrolled_in_course and lms_user and not batch.students.filter(id=lms_user.id).exists():
        batch.students.add(lms_user)

    context = {
        'lms_user': lms_user,
        'is_admin': is_admin,
        'is_mentor': is_mentor,
        'is_student': is_student,
        'session_form': BatchSessionForm(initial={'batch': batch}),
        'material_form': BatchMaterialForm(initial={'batch': batch}),
        'assignment_form': BatchAssignmentForm(batch=batch, initial={'batch': batch}),
        'assign_form': BatchAssignMembersForm(initial={
            'students': batch.students.all(),
            'mentors': batch.mentors.all(),
        }),
        **detail_data,
    }
    return render(request, 'lms/batch_detail.html', context)


@login_required
@lms_role_required(allowed_roles=['ADMIN', 'MANAGER', 'MENTOR', 'INSTRUCTOR'])
def add_batch_assignment_view(request, batch_id):
    batch = get_object_or_404(Batch, pk=batch_id)
    if request.method == 'POST':
        form = BatchAssignmentForm(request.POST, batch=batch)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.batch = batch
            lms_user = get_lms_user(request.user)
            assignment.assigned_by = lms_user
            assign_target = form.cleaned_data.get('assign_target', 'ALL')
            if assign_target == 'ALL':
                assignment.target_student = None
            assignment.save()
            target_desc = "All Students in Batch" if not assignment.target_student else assignment.target_student.full_name
            messages.success(request, f"Assignment '{assignment.title}' successfully assigned to {target_desc}!")
        else:
            messages.error(request, f"Failed to assign task: {form.errors.as_text()}")
    return redirect(request.POST.get('next') or f"/lms/batches/{batch_id}/")


@login_required
@lms_role_required(allowed_roles=['ADMIN', 'MANAGER', 'MENTOR', 'INSTRUCTOR'])
def delete_batch_assignment_view(request, batch_id, pk):
    assignment = get_object_or_404(BatchAssignment, pk=pk, batch_id=batch_id)
    if request.method == 'POST':
        assignment.delete()
        messages.success(request, "Assignment removed.")
    return redirect(request.POST.get('next') or f"/lms/batches/{batch_id}/")


@login_required
@lms_role_required(allowed_roles=['ADMIN', 'MANAGER', 'MENTOR', 'INSTRUCTOR'])
def mark_session_attendance_view(request, batch_id):
    batch = get_object_or_404(Batch, pk=batch_id)
    session_id = request.POST.get('session_id')
    if not session_id:
        messages.error(request, "No class session was selected.")
        return redirect(request.POST.get('next') or f"/lms/batches/{batch_id}/")

    session = get_object_or_404(BatchSession, pk=session_id, batch=batch)
    lms_user = get_lms_user(request.user)

    students = batch.students.filter(is_active=True)
    present_count = 0
    absent_count = 0
    late_count = 0

    for s in students:
        status = request.POST.get(f"status_{s.id}", "PRESENT")
        notes = request.POST.get(f"notes_{s.id}", "").strip()
        SessionAttendance.objects.update_or_create(
            session=session,
            student=s,
            defaults={
                'status': status,
                'marked_by': lms_user,
                'notes': notes,
            }
        )
        if status == 'PRESENT':
            present_count += 1
        elif status == 'ABSENT':
            absent_count += 1
        elif status == 'LATE':
            late_count += 1

    msg = f"Attendance recorded for '{session.title}': {present_count} Present, {absent_count} Absent, {late_count} Late out of {students.count()} students."
    messages.success(request, msg)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('format') == 'json':
        return JsonResponse({
            'success': True,
            'message': msg,
            'present_count': present_count,
            'absent_count': absent_count,
            'late_count': late_count,
            'total_students': students.count(),
        })

    return redirect(request.POST.get('next') or f"/lms/batches/{batch_id}/")


@login_required
@lms_role_required(allowed_roles=['ADMIN', 'MANAGER', 'MENTOR', 'INSTRUCTOR'])
def assess_batch_assignment_view(request, batch_id):
    """
    Allows instructors / mentors to assess/grade students per assignment:
    - Can grade the whole cohort for an assignment, or evaluate an individual student.
    - Saves score, status (GRADED, REVISION_REQUESTED, EXCUSED), and mentor feedback.
    """
    batch = get_object_or_404(Batch, pk=batch_id)
    assignment_id = request.POST.get('assignment_id')
    assignment = get_object_or_404(BatchAssignment, pk=assignment_id, batch=batch)
    lms_user = get_lms_user(request.user)

    single_student_id = request.POST.get('student_id')
    if single_student_id:
        target_students = batch.students.filter(pk=single_student_id, is_active=True)
    else:
        target_students = [assignment.target_student] if assignment.target_student else batch.students.filter(is_active=True)

    assessed_count = 0
    for s in target_students:
        score_val = request.POST.get(f"score_{s.id}")
        if score_val is None and single_student_id:
            score_val = request.POST.get("score")

        status = request.POST.get(f"status_{s.id}")
        if not status and single_student_id:
            status = request.POST.get("status")
        if not status:
            status = 'GRADED'

        feedback = request.POST.get(f"feedback_{s.id}")
        if feedback is None and single_student_id:
            feedback = request.POST.get("mentor_feedback")
        feedback = (feedback or "").strip()

        score = None
        if score_val is not None and score_val != '':
            try:
                score = int(score_val)
            except (ValueError, TypeError):
                score = None

        BatchAssignmentAssessment.objects.update_or_create(
            assignment=assignment,
            student=s,
            defaults={
                'score': score,
                'max_score': assignment.max_score,
                'status': status,
                'mentor_feedback': feedback,
                'assessed_by': lms_user,
            }
        )
        assessed_count += 1

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('accept', ''):
        return JsonResponse({
            'status': 'success',
            'message': f"Assessment saved for '{assignment.title}' ({assessed_count} evaluated).",
            'score': score if single_student_id else None,
            'max_score': assignment.max_score,
            'assessment_status': status if single_student_id else 'GRADED',
        })

    messages.success(request, f"Assessment saved for '{assignment.title}' ({assessed_count} evaluated).")
    return redirect(request.POST.get('next') or f"/lms/batches/{batch_id}/#tab-assignments")


# =========================================================================================
# BATCH SESSIONS & MATERIALS VIEWS
# =========================================================================================

@login_required
@lms_role_required(allowed_roles=['ADMIN', 'MANAGER', 'MENTOR'])
def add_batch_session_view(request, batch_id=None):
    if not batch_id:
        batch_id = request.POST.get('batch_id')
    batch = get_object_or_404(Batch, pk=batch_id)
    if request.method == 'POST':
        form = BatchSessionForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.batch = batch
            session.save()
            messages.success(request, f"Scheduled session '{session.title}' for batch {batch.code}!")
        else:
            messages.error(request, f"Failed to schedule session: {form.errors.as_text()}")
    return redirect(request.POST.get('next') or f"/lms/batches/{batch_id}/")


@login_required
@lms_role_required(allowed_roles=['ADMIN', 'MANAGER', 'MENTOR'])
def edit_batch_session_view(request, pk):
    session = get_object_or_404(BatchSession, pk=pk)
    if request.method == 'POST':
        form = BatchSessionForm(request.POST, instance=session)
        if form.is_valid():
            form.save()
            messages.success(request, f"Updated session '{session.title}'.")
        else:
            messages.error(request, f"Error updating session: {form.errors.as_text()}")
    return redirect(request.POST.get('next') or f"/lms/batches/{session.batch_id}/")


@login_required
@lms_role_required(allowed_roles=['ADMIN', 'MANAGER', 'MENTOR'])
def delete_batch_session_view(request, pk):
    session = get_object_or_404(BatchSession, pk=pk)
    batch_id = session.batch_id
    if request.method == 'POST':
        session.delete()
        messages.success(request, "Session removed.")
    return redirect(request.POST.get('next') or f"/lms/batches/{batch_id}/")


@login_required
@lms_role_required(allowed_roles=['ADMIN', 'MANAGER', 'MENTOR'])
def add_batch_material_view(request, batch_id=None):
    target_batch_id = batch_id or request.POST.get('batch') or request.POST.get('batch_id')
    if not target_batch_id:
        messages.error(request, "Target batch is required to upload materials.")
        return redirect(request.POST.get('next') or '/lms/?tab=materials')
    batch = get_object_or_404(Batch, pk=target_batch_id)
    lms_user = get_lms_user(request.user)
    if request.method == 'POST':
        form = BatchMaterialForm(request.POST, request.FILES)
        if form.is_valid():
            material = form.save(commit=False)
            material.batch = batch
            material.uploaded_by = lms_user
            material.save()
            messages.success(request, f"Added material '{material.title}' to batch {batch.code}!")
        else:
            messages.error(request, f"Failed to upload material: {form.errors.as_text()}")
    return redirect(request.POST.get('next') or f"/lms/batches/{batch.id}/")


@login_required
@lms_role_required(allowed_roles=['ADMIN', 'MANAGER', 'MENTOR'])
def delete_batch_material_view(request, pk):
    material = get_object_or_404(BatchMaterial, pk=pk)
    batch_id = material.batch_id
    if request.method == 'POST':
        material.delete()
        messages.success(request, "Material removed.")
    return redirect(request.POST.get('next') or f"/lms/batches/{batch_id}/")


# =========================================================================================
# STUDENT & MENTOR MANAGEMENT & PASSWORD RESET VIEWS
# =========================================================================================

@login_required
@lms_role_required(allowed_roles=['ADMIN', 'MANAGER'])
def add_cohort_user_view(request):
    from core.models import User as CoreUser
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        role = request.POST.get('role', 'STUDENT')
        phone = request.POST.get('phone', '').strip()
        specialization = request.POST.get('specialization', '').strip()
        password = request.POST.get('password', '').strip() or 'AclMission@123'
        batch_id = request.POST.get('batch_id')
        initial_fee = request.POST.get('initial_fee', '').strip()

        if not email:
            messages.error(request, "Email address is required.")
            return redirect('/lms/?tab=students')

        # 1. Core User
        core_user = CoreUser.objects.filter(email=email).first()
        if not core_user:
            core_user = CoreUser(
                email=email,
                first_name=first_name,
                last_name=last_name,
                is_active=True,
                is_staff=(role == 'ADMIN'),
                is_superuser=(role == 'ADMIN'),
            )
            core_user.set_password(password)
            core_user.save()
        else:
            core_user.first_name = first_name or core_user.first_name
            core_user.last_name = last_name or core_user.last_name
            core_user.set_password(password)
            core_user.save()

        # 2. LMS User
        lms_user, _ = LMSUser.objects.update_or_create(
            external_user_id=core_user.id,
            defaults={
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'role': role,
                'phone': phone,
                'specialization': specialization,
                'avatar_url': f"https://ui-avatars.com/api/?name={first_name}+{last_name}&background=1e293b&color=38bdf8",
                'is_active': True,
            }
        )

        # 3. Assign Batch if provided
        if batch_id:
            batch = Batch.objects.filter(id=batch_id, is_active=True).first()
            if batch:
                if role == 'MENTOR':
                    batch.mentors.add(lms_user)
                else:
                    batch.students.add(lms_user)
                sync_batch_course_and_enrollments(batch)

        # 4. Optional Initial Fee Creation for Students
        if initial_fee:
            try:
                fee_val = Decimal(initial_fee)
                if fee_val > 0:
                    StudentPayment.objects.create(
                        student=lms_user,
                        batch_id=batch_id if batch_id else None,
                        title="Program Enrollment Fee",
                        total_amount=fee_val,
                        amount_paid=Decimal('0.00'),
                        payment_status='PENDING',
                    )
            except Exception:
                pass

        target_tab = 'mentors' if role == 'MENTOR' else 'students'
        messages.success(request, f"Successfully created {role.capitalize()} account for {email} with password '{password}'.")
        return redirect(f"/lms/?tab={target_tab}")

    return redirect('/lms/?tab=students')


@login_required
@lms_role_required(allowed_roles=['ADMIN', 'MANAGER'])
def edit_cohort_user_view(request, pk):
    from core.models import User as CoreUser
    lms_user = get_object_or_404(LMSUser, pk=pk)

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        role = request.POST.get('role', lms_user.role)
        phone = request.POST.get('phone', '').strip()
        specialization = request.POST.get('specialization', '').strip()
        bio = request.POST.get('bio', '').strip()
        batch_id = request.POST.get('batch_id')

        # Update core user
        core_user = CoreUser.objects.filter(id=lms_user.external_user_id).first()
        if core_user:
            core_user.first_name = first_name
            core_user.last_name = last_name
            if email and email != core_user.email:
                core_user.email = email
            core_user.save()

        # Update LMS profile
        lms_user.first_name = first_name
        lms_user.last_name = last_name
        lms_user.email = email or lms_user.email
        lms_user.role = role
        lms_user.phone = phone
        lms_user.specialization = specialization
        lms_user.bio = bio
        lms_user.save()

        # Update batch association
        if batch_id:
            batch = Batch.objects.filter(id=batch_id, is_active=True).first()
            if batch:
                if role == 'MENTOR':
                    batch.mentors.add(lms_user)
                else:
                    batch.students.add(lms_user)
                sync_batch_course_and_enrollments(batch)

        target_tab = 'mentors' if role == 'MENTOR' else 'students'
        messages.success(request, f"Profile details for {lms_user.email} updated.")
        return redirect(request.POST.get('next') or f"/lms/?tab={target_tab}")

    return redirect('/lms/?tab=students')


@login_required
@lms_role_required(allowed_roles=['ADMIN', 'MANAGER'])
def reset_cohort_user_password_view(request, pk):
    from core.models import User as CoreUser
    lms_user = get_object_or_404(LMSUser, pk=pk)

    if request.method == 'POST':
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()

        if not new_password or len(new_password) < 6:
            messages.error(request, "Password must be at least 6 characters long.")
            return redirect(request.POST.get('next') or '/lms/?tab=students')

        if new_password != confirm_password:
            messages.error(request, "New password and confirmation do not match.")
            return redirect(request.POST.get('next') or '/lms/?tab=students')

        core_user = CoreUser.objects.filter(id=lms_user.external_user_id).first()
        if core_user:
            core_user.set_password(new_password)
            core_user.save()
            messages.success(request, f"Password for {lms_user.email} reset successfully to '{new_password}'.")
        else:
            messages.error(request, "Underlying authentication account could not be found.")

    target_tab = 'mentors' if lms_user.role == 'MENTOR' else 'students'
    return redirect(request.POST.get('next') or f"/lms/?tab={target_tab}")


# =========================================================================================
# PAYMENT & FEE MANAGEMENT VIEWS
# =========================================================================================

@login_required
@lms_role_required(allowed_roles=['ADMIN', 'MANAGER'])
def record_student_payment_view(request):
    if request.method == 'POST':
        payment_id = request.POST.get('payment_id')
        if payment_id:
            payment = get_object_or_404(StudentPayment, pk=payment_id)
            form = StudentPaymentRecordForm(request.POST, instance=payment)
        else:
            form = StudentPaymentRecordForm(request.POST)

        if form.is_valid():
            payment = form.save(commit=False)
            if payment.amount_paid >= payment.total_amount and payment.total_amount > 0:
                payment.payment_status = 'PAID'
                if not payment.paid_at:
                    payment.paid_at = timezone.now()
            elif payment.amount_paid > 0:
                payment.payment_status = 'PARTIAL'
            payment.save()
            messages.success(request, f"Payment record for {payment.student.full_name} saved successfully!")
        else:
            messages.error(request, f"Failed to save payment: {form.errors.as_text()}")

    return redirect('/lms/?tab=payments')


@login_required
def student_payments_view(request):
    lms_user = get_lms_user(request.user)
    is_admin = request.user.is_staff or request.user.is_superuser or (lms_user and lms_user.role in ['ADMIN', 'MANAGER'])

    # Tuition and fee records are restricted to academic administrators
    if not is_admin:
        messages.info(request, "Tuition and fee records are managed directly by academic administration.")
        return redirect('lms:dashboard')

    # Handle Student Payment Proof submission
    if request.method == 'POST':
        payment_id = request.POST.get('payment_id')
        payment = get_object_or_404(StudentPayment, pk=payment_id)

        # Ensure user owns payment or is admin
        if not is_admin and payment.student_id != lms_user.id:
            messages.error(request, "Unauthorized payment modification.")
            return redirect('/lms/payments/')

        amount_str = request.POST.get('amount_paid', '0').strip()
        method = request.POST.get('payment_method', 'UPI')
        txn_ref = request.POST.get('transaction_reference', '').strip()
        notes = request.POST.get('notes', '').strip()

        try:
            amount = Decimal(amount_str)
            payment.amount_paid = amount
            payment.payment_method = method
            payment.transaction_reference = txn_ref
            payment.paid_at = timezone.now()
            if notes:
                payment.notes = f"{payment.notes}\n[Student Note]: {notes}".strip()

            if amount >= payment.total_amount and payment.total_amount > 0:
                payment.payment_status = 'PAID'
            elif amount > 0:
                payment.payment_status = 'PARTIAL'

            payment.save()
            messages.success(request, f"Payment proof submitted successfully! Transaction reference: {txn_ref}.")
        except Exception as e:
            messages.error(request, f"Invalid payment submission: {str(e)}")

        return redirect('/lms/payments/')

    # GET: Student views payments or Admin views payment list
    if is_admin:
        admin_data = get_admin_dashboard_data()
        context = {
            'lms_user': lms_user,
            'is_admin': True,
            'payments': admin_data['payments'],
            'payment_stats': admin_data['payment_stats'],
            'payment_form': StudentPaymentRecordForm(),
        }
        return render(request, 'lms/student_payments.html', context)

    payment_data = get_student_payment_data(request.user.id)
    context = {
        'lms_user': lms_user,
        'is_admin': False,
        **payment_data,
    }
    return render(request, 'lms/student_payments.html', context)

