import uuid
from django.utils import timezone
from .models import (
    LMSUser,
    Course,
    Module,
    Lesson,
    Enrollment,
    LessonProgress,
    AssignmentSubmission,
    Certificate,
    StudentActivity,
    CourseCommandMessage,
    CourseInstructor,
    BatchMaterial,
)


def sync_lms_user(user, role=None):
    """
    Synchronizes core.User data into lms.LMSUser without cross-database foreign keys.
    """
    if not user:
        return None

    lms_user, created = LMSUser.objects.get_or_create(
        external_user_id=user.id,
        defaults={
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': role or ('ADMIN' if user.is_superuser or user.is_staff else 'STUDENT'),
        }
    )

    if not created:
        lms_user.email = user.email
        if user.first_name:
            lms_user.first_name = user.first_name
        if user.last_name:
            lms_user.last_name = user.last_name
        if role:
            lms_user.role = role
        lms_user.save()

    return lms_user


def calculate_course_progress(enrollment):
    """
    Implements Formula 7.1:
    Course Progress (%) = round((Completed Required Lessons in Course / Total Required Lessons in Course) * 100)
    """
    required_lessons = Lesson.objects.filter(
        module__course=enrollment.course,
        is_required=True,
        is_active=True
    )
    total_required = required_lessons.count()

    if total_required == 0:
        progress_percent = 0
    else:
        completed_required = LessonProgress.objects.filter(
            enrollment=enrollment,
            lesson__in=required_lessons,
            completed=True
        ).count()
        progress_percent = round((completed_required / total_required) * 100)

    enrollment.progress_percent = progress_percent

    # Update status and issue certificate if completed
    if progress_percent == 100:
        enrollment.status = 'COMPLETED'
        if not Certificate.objects.filter(enrollment=enrollment).exists():
            cert_no = f"CERT-{enrollment.course.code}-{enrollment.external_user_id}-{uuid.uuid4().hex[:8].upper()}"
            Certificate.objects.create(
                enrollment=enrollment,
                certificate_number=cert_no
            )
    elif enrollment.status == 'COMPLETED' and progress_percent < 100:
        enrollment.status = 'ACTIVE'

    enrollment.save(update_fields=['progress_percent', 'status', 'updated_at'])
    return progress_percent


def calculate_overall_progress(external_user_id):
    """
    Implements Formula 7.2:
    Overall Progress (%) = round((Sum of Completed Required Lessons / Sum of Total Required Lessons) * 100)
    """
    enrollments = Enrollment.objects.filter(external_user_id=external_user_id, is_active=True)
    if not enrollments.exists():
        return 0

    sum_total = 0
    sum_completed = 0

    for enrollment in enrollments:
        req_lessons = Lesson.objects.filter(
            module__course=enrollment.course,
            is_required=True,
            is_active=True
        )
        total_in_course = req_lessons.count()
        if total_in_course > 0:
            sum_total += total_in_course
            completed_in_course = LessonProgress.objects.filter(
                enrollment=enrollment,
                lesson__in=req_lessons,
                completed=True
            ).count()
            sum_completed += completed_in_course

    if sum_total == 0:
        return 0
    return round((sum_completed / sum_total) * 100)


def mark_lesson_completed(enrollment, lesson):
    """
    Workflow 7.3: Upsert LessonProgress, recalculate course progress, create StudentActivity.
    """
    progress, _ = LessonProgress.objects.get_or_create(
        enrollment=enrollment,
        lesson=lesson
    )
    progress.completed = True
    progress.completed_at = timezone.now()
    progress.save()

    new_percent = calculate_course_progress(enrollment)

    # Activity record
    StudentActivity.objects.create(
        external_user_id=enrollment.external_user_id,
        activity_type='LESSON_COMPLETED',
        title=f"Completed: {lesson.title}",
        detail=f"Module: {lesson.module.title} • {lesson.module.course.code}",
    )

    return progress, new_percent


def submit_assignment(assignment, external_user_id, submission_url, submission_text):
    """
    Workflow 9.1 & 9.2: Upsert assignment submission, reset status to SUBMITTED, update notes and URL.
    """
    submission, _ = AssignmentSubmission.objects.get_or_create(
        assignment=assignment,
        external_user_id=external_user_id,
        defaults={
            'submission_url': submission_url,
            'submission_text': submission_text,
            'status': 'SUBMITTED',
        }
    )

    submission.submission_url = submission_url
    submission.submission_text = submission_text
    submission.status = 'SUBMITTED'
    submission.mentor_feedback = ''
    submission.submitted_at = timezone.now()
    submission.save()

    StudentActivity.objects.create(
        external_user_id=external_user_id,
        activity_type='ASSIGNMENT_SUBMITTED',
        title=f"Submitted Assignment: {assignment.title}",
        detail=f"Course: {assignment.course.code}",
    )

    return submission


def grade_submission(submission, grade_score, mentor_feedback):
    """
    Workflow 9.1: Grade submission with score and mentor feedback.
    Approved if grade_score / max_score >= 0.70.
    """
    if grade_score < 0 or grade_score > submission.assignment.max_score:
        raise ValueError(f"Score must be between 0 and {submission.assignment.max_score}")

    ratio = grade_score / submission.assignment.max_score if submission.assignment.max_score > 0 else 1.0
    if ratio >= 0.70:
        submission.status = 'REVIEWED'
    else:
        submission.status = 'REVISION_REQUESTED'

    submission.grade_score = grade_score
    submission.mentor_feedback = mentor_feedback
    submission.save()

    StudentActivity.objects.create(
        external_user_id=submission.external_user_id,
        activity_type='ASSIGNMENT_GRADED',
        title=f"Feedback on: {submission.assignment.title}",
        detail=f"Status: {submission.get_status_display()}",
        score=f"{grade_score}/{submission.assignment.max_score}",
    )

    return submission


def publish_command_message(course, title, previous_session_summary, previous_session_recording_url,
                            next_class_topic, next_class_datetime, next_class_link, published_by_id):
    """
    Deactivates existing command messages for course and activates a new one.
    """
    CourseCommandMessage.objects.filter(course=course).update(is_active=False)

    return CourseCommandMessage.objects.create(
        course=course,
        title=title,
        previous_session_summary=previous_session_summary,
        previous_session_recording_url=previous_session_recording_url,
        next_class_topic=next_class_topic,
        next_class_datetime=next_class_datetime,
        next_class_link=next_class_link,
        published_by_id=published_by_id,
        is_active=True,
    )


def sync_batch_course_and_enrollments(batch):
    """
    Ensures that every batch is linked to a published Course,
    and all students enrolled in the batch are automatically enrolled in that Course.
    Also ensures assigned mentors are linked as course instructors.
    """
    if not batch:
        return None

    from django.utils.text import slugify
    from .models import Course, Enrollment, CourseInstructor

    if not batch.course:
        base_slug = slugify(batch.name) or f"course-{batch.code.lower()}"
        slug = base_slug
        counter = 1
        while Course.objects.filter(slug=slug).exclude(batches=batch).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        course, _ = Course.objects.get_or_create(
            code=batch.code,
            defaults={
                'title': batch.name,
                'slug': slug,
                'status': 'PUBLISHED',
                'difficulty_level': 'INTERMEDIATE',
                'short_description': batch.description or f"Comprehensive curriculum and labs for {batch.name}",
                'description': batch.description or f"Official curriculum for cohort {batch.code}.",
                'thumbnail': 'genai.svg',
                'is_active': True,
            }
        )
        batch.course = course
        batch.save(update_fields=['course'])

    course = batch.course
    if course:
        # Guarantee course is active and published
        if course.status != 'PUBLISHED' or not course.is_active:
            course.status = 'PUBLISHED'
            course.is_active = True
            course.save(update_fields=['status', 'is_active'])

        # Auto-enroll all batch students into the course
        for student in batch.students.all():
            if student.external_user_id:
                Enrollment.objects.get_or_create(
                    external_user_id=student.external_user_id,
                    course=course,
                    defaults={'status': 'ACTIVE', 'progress_percent': 0}
                )

        # Link all batch mentors as CourseInstructors
        for mentor in batch.mentors.all():
            CourseInstructor.objects.get_or_create(
                course=course,
                instructor=mentor,
                defaults={'role': 'LEAD', 'is_primary': False}
            )

    return course


def import_course_materials_from_path(course, directory_path, batch=None):
    """
    Parses and imports course curriculum materials (chapters, lessons, labs)
    from a local directory path into Course Modules, Lessons, and BatchMaterials.
    Supports day_*.html files, markdown files, and structured materials.
    """
    import os
    import re
    from bs4 import BeautifulSoup

    if not os.path.exists(directory_path) or not os.path.isdir(directory_path):
        return {'success': False, 'error': f"Directory path '{directory_path}' does not exist or is not a directory."}

    day_files = sorted([
        f for f in os.listdir(directory_path)
        if (f.startswith('day_') or f.startswith('chapter_') or f.startswith('lesson_')) and f.endswith('.html')
    ])

    if not day_files:
        day_files = sorted([f for f in os.listdir(directory_path) if f.endswith(('.html', '.md')) and not f.startswith('index')])

    if not day_files:
        return {'success': False, 'error': f"No lesson or chapter files found in '{directory_path}'."}

    # Define 4 core phases / modules for a comprehensive engineering masterclass
    phase_defs = [
        (1, 8, "Phase 1: Foundations & Deterministic Loops", "Python fundamentals, LLM mechanics, prompt engineering, structured outputs, and autonomous problem solver CLI capstone."),
        (9, 16, "Phase 2: Autonomous Reasoning, RAG & Tool Orchestration", "ReAct loops, semantic registries, vector RAG pipelines, LangChain, n8n automation, and multi-silo knowledge agent capstone."),
        (17, 20, "Phase 3: Stateful Graphs & Multi-Agent Swarms", "LangGraph cyclic graphs, checkpoint persistence, memory, swarm architectures, security guardrails, and human-in-the-loop gates."),
        (21, 24, "Phase 4: Production, Security, CI/CD & Enterprise Deployment", "FastAPI streaming UI, multi-stage Docker, observability, evaluations, CI/CD pipelines, and enterprise automotive assistant grand capstone."),
    ]

    modules_by_day = {}
    for mod_order, (start_d, end_d, title, desc) in enumerate(phase_defs, start=1):
        module, _ = Module.objects.get_or_create(
            course=course,
            title=title,
            defaults={'order': mod_order, 'description': desc}
        )
        for d in range(start_d, end_d + 1):
            modules_by_day[d] = module

    default_module, _ = Module.objects.get_or_create(
        course=course,
        title=f"{course.title} - Core Curriculum",
        defaults={'order': 99, 'description': "Curriculum chapters and practical labs."}
    )

    lessons_created = 0
    lessons_updated = 0

    for file_name in day_files:
        file_path = os.path.join(directory_path, file_name)
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as fp:
                raw_html = fp.read()
        except Exception:
            continue

        soup = BeautifulSoup(raw_html, 'html.parser')

        day_num_match = re.search(r'(?:day|chapter|lesson)[_-]?(\d+)', file_name, re.I)
        day_num = int(day_num_match.group(1)) if day_num_match else (lessons_created + 1)

        title = ''
        title_tag = soup.find('title')
        h1_tag = soup.find('h1')
        if title_tag and title_tag.string:
            title = title_tag.string.strip()
        elif h1_tag:
            title = h1_tag.get_text().strip()
        else:
            title = f"Day {day_num}: {file_name.replace('.html', '').replace('_', ' ').title()}"

        clean_title = re.sub(r'^(Day\s+\d+:\s*)+', f'Day {day_num}: ', title, flags=re.I)

        article_tag = soup.find('article', class_=re.compile(r'book-page|content', re.I)) or soup.find('article') or soup.find('main') or soup.find('body')
        if article_tag:
            for bad_tag in article_tag.find_all(['script', 'nav', 'header', 'noscript', 'button']):
                bad_tag.decompose()
            lesson_content = str(article_tag)
        else:
            lesson_content = raw_html

        # Remap relative asset images to static folder
        lesson_content = re.sub(r'src=["\'](?:\.?/)?assets/', 'src="/static/material_assets/', lesson_content)

        is_lab = any(kw in clean_title.lower() for kw in ['project', 'capstone', 'lab', 'milestone', 'hands-on'])
        lesson_type = 'LAB' if is_lab else 'ARTICLE'
        duration = 120 if is_lab else 45

        target_module = modules_by_day.get(day_num, default_module)

        lesson, created = Lesson.objects.update_or_create(
            module=target_module,
            order=day_num,
            defaults={
                'title': clean_title,
                'lesson_type': lesson_type,
                'duration_minutes': duration,
                'content': lesson_content,
                'is_required': True,
            }
        )

        if created:
            lessons_created += 1
        else:
            lessons_updated += 1

        if not batch:
            batch = course.batches.first()

        if batch:
            BatchMaterial.objects.get_or_create(
                batch=batch,
                title=f"{clean_title} (Day {day_num} Material)",
                defaults={
                    'material_type': 'DOCUMENT',
                    'description': f"Official curriculum reading and labs for Day {day_num}.",
                    'external_url': f"file://{file_path}",
                }
            )

    return {
        'success': True,
        'lessons_created': lessons_created,
        'lessons_updated': lessons_updated,
        'total_lessons': Lesson.objects.filter(module__course=course).count(),
        'modules_count': course.modules.count(),
        'directory': directory_path,
    }

