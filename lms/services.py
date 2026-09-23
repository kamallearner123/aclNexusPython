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


def submit_assignment(assignment, external_user_id, submission_url, submission_text, github_path=''):
    """
    Workflow 9.1 & 9.2: Upsert assignment submission, reset status to SUBMITTED, update notes, path, and URL.
    """
    submission, _ = AssignmentSubmission.objects.get_or_create(
        assignment=assignment,
        external_user_id=external_user_id,
        defaults={
            'submission_url': submission_url,
            'github_path': github_path,
            'submission_text': submission_text,
            'status': 'SUBMITTED',
        }
    )

    submission.submission_url = submission_url
    submission.github_path = github_path
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

    # Check if this is Embedded C Programming or Embedded Systems or AI course
    is_embedded_c = (
        any('embedded c' in s.lower() or 'embedded-c' in s.lower() for s in [course.code, course.title, directory_path])
        or any(f.startswith('topic_') for f in os.listdir(directory_path) if f.endswith('.html'))
    )
    is_embedded_sys = not is_embedded_c and any('embedded' in s.lower() for s in [course.code, course.title, directory_path])

    if is_embedded_c:
        embedded_c_modules = [
            (1, "Module 1: Foundations & Discipline", "Constrained systems prelude, C history and tools, best practices, error taxonomy, assertions, logging, unit testing, and hardware diagnostics milestone.",
             [("intro.html", False, 45), ("topic_01.html", False, 45), ("topic_02.html", False, 45), ("topic_03.html", False, 45), ("topic_04.html", False, 45), ("topic_05.html", False, 45), ("project_01.html", True, 120)]),
            (2, "Module 2: Toolchains & Binaries", "The complete compilation pipeline, GCC cross-compilers, binary utilities (objdump, size, nm, GDB), Make and CMake, Git workflows, and linker script milestone.",
             [("topic_06.html", False, 45), ("topic_07.html", False, 45), ("topic_08.html", False, 45), ("topic_09.html", False, 45), ("topic_10.html", False, 45), ("project_02.html", True, 120)]),
            (3, "Module 3: Reactive & Event-Driven Systems", "Event loop design, polling versus interrupts, asynchronous hardware callbacks, software timers, non-blocking firmware execution, and ring buffer milestone.",
             [("topic_11.html", False, 45), ("topic_12.html", False, 45), ("topic_13.html", False, 45), ("topic_14.html", False, 45), ("project_03.html", True, 120)]),
            (4, "Module 4: Standards & State Machines", "Firmware style conventions, defensive programming patterns, Doxygen documentation, MISRA-C safety guidelines, finite state machines, state transition tables, and defensive controller milestone.",
             [("topic_15.html", False, 45), ("topic_16.html", False, 45), ("topic_17.html", False, 45), ("topic_18.html", False, 45), ("topic_19.html", False, 45), ("topic_20.html", False, 45), ("project_04.html", True, 120)]),
            (5, "Module 5: Architecture & Integration", "Modular header and source decoupling, hardware abstraction interfaces, reusable component libraries, Application/Driver/HAL/BSP layering, and integrated production firmware capstone.",
             [("topic_21.html", False, 45), ("topic_22.html", False, 45), ("topic_23.html", False, 45), ("topic_24.html", False, 45), ("topic_25.html", False, 45), ("project_05.html", True, 120)]),
            (6, "Module 6: Hardware & Engineering Reference Compendium", "Comprehensive hardware reference compendium: Silicon architectures (MCU vs MPU), sensors and transducers, actuators and power drivers, 20 industrial hardware architectures, and protocol standards.",
             [("reference.html", False, 60), ("ref_sensors.html", False, 45), ("ref_actuators.html", False, 45), ("ref_silicon.html", False, 45), ("ref_devices.html", False, 60), ("ref_standards.html", False, 45)]),
            (7, "Module 7: Interactive Lab & Capstone", "The complete STM32 firmware execution journey: from C source compilation and linker mapping down to reset vectors, SRAM initialization, register manipulation, and interactive hardware simulation.",
             [("stm32-firmware-journey.html", True, 180)]),
        ]

        modules_by_file = {}
        file_metadata = {}
        global_order = 0
        for mod_order, title, desc, items in embedded_c_modules:
            mod, _ = Module.objects.update_or_create(
                course=course,
                order=mod_order,
                defaults={'title': title, 'description': desc, 'is_active': True}
            )
            for fname, is_lab, duration in items:
                global_order += 1
                modules_by_file[fname] = mod
                file_metadata[fname] = (global_order, is_lab, duration)

        ordered_files = [fname for _, _, _, items in embedded_c_modules for fname, _, _ in items]
        available_files = [f for f in ordered_files if os.path.exists(os.path.join(directory_path, f))]

        lessons_created = 0
        lessons_updated = 0
        if not batch:
            batch = course.batches.first()

        for fname in available_files:
            file_path = os.path.join(directory_path, fname)
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as fp:
                    raw_html = fp.read()
            except Exception:
                continue

            soup = BeautifulSoup(raw_html, 'html.parser')
            t_tag = soup.find('title')
            h1_tag = soup.find('h1')
            if t_tag and t_tag.string:
                title = t_tag.string.strip()
            elif h1_tag:
                title = h1_tag.get_text().strip()
            else:
                title = fname.replace('.html', '').replace('_', ' ').title()

            clean_title = re.sub(r'\s*-\s*Embedded C Programming.*$', '', title, flags=re.I).strip()

            if fname == 'stm32-firmware-journey.html':
                main_tag = soup.find('main', class_=re.compile(r'content-area', re.I)) or soup.find('main') or soup.find('body')
                style_tag = soup.find('style')
                script_tag = soup.find('script', src=None)
                parts = []
                if style_tag:
                    parts.append(str(style_tag))
                if main_tag:
                    tb = main_tag.find('button', id='theme-btn')
                    if tb:
                        tb.decompose()
                    parts.append(str(main_tag))
                else:
                    parts.append(raw_html)
                if script_tag:
                    parts.append(str(script_tag))
                lesson_content = "\n".join(parts)
            else:
                art = soup.find('article', class_=re.compile(r'book-page|content', re.I)) or soup.find('article') or soup.find('main')
                if art:
                    for bad in art.find_all(['nav', 'header', 'noscript']):
                        bad.decompose()
                    for btn in art.find_all('button', class_='mcq-submit'):
                        btn.decompose()
                    lesson_content = str(art)
                else:
                    lesson_content = raw_html

            lesson_content = re.sub(r'src=["\'](?:\.?/)?images/', 'src="/static/img/courses/embedded-c/', lesson_content)

            lesson_order, is_lab, duration = file_metadata.get(fname, (lessons_created + 1, False, 45))
            lesson_type = 'LAB' if is_lab else 'ARTICLE'
            target_module = modules_by_file.get(fname)

            lesson, created = Lesson.objects.update_or_create(
                module=target_module,
                order=lesson_order,
                defaults={
                    'title': clean_title,
                    'lesson_type': lesson_type,
                    'duration_minutes': duration,
                    'content': lesson_content,
                    'is_required': True,
                    'is_active': True,
                }
            )
            if created:
                lessons_created += 1
            else:
                lessons_updated += 1

            if batch:
                BatchMaterial.objects.update_or_create(
                    batch=batch,
                    title=f"{clean_title} (Course Material)",
                    defaults={
                        'material_type': 'DOCUMENT',
                        'description': f"Official curriculum readings and labs for {clean_title}.",
                        'external_url': f"file://{file_path}",
                        'is_active': True,
                    }
                )

        return {
            'success': True,
            'lessons_created': lessons_created,
            'lessons_updated': lessons_updated,
            'modules_count': course.modules.count(),
        }

    elif is_embedded_sys:
        phase_defs = [
            (1, 8, "Module 1: Embedded C Foundations & Hardware Fundamentals", "Bare-metal C programming, memory architectures, register manipulation, GPIO, interrupts, timers, ADC/DAC, and communication protocols."),
            (9, 16, "Module 2: RTOS, Peripherals & Communication Protocols", "FreeRTOS fundamentals, task scheduling, synchronization primitives, DMA, automotive CAN bus, USB/wireless, bootloaders, and RTOS sensor hub capstone."),
            (17, 24, "Module 3: Advanced Topics, Safety, Debugging & Capstone", "Low-power system design, Flash/EEPROM/FatFS, MISRA-C safety-critical firmware, JTAG/SWD debugging, unit testing with Unity/CMock, embedded Linux, and automotive ECU grand capstone."),
        ]
    else:
        # 4 core phases / modules for Agentic AI engineering masterclass
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

