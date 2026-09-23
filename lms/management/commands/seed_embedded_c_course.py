import os
import re
from datetime import date
from django.core.management.base import BaseCommand
from bs4 import BeautifulSoup
from lms.models import (
    Course,
    Module,
    Lesson,
    CourseInstructor,
    Batch,
    BatchMaterial,
    Enrollment,
    LMSUser
)

DEFAULT_COURSE_DIR = "/Users/kamalmukiri/Documents/1.GitHub/acl-tech-books/acl-tech-books/Embedded C Programming"

MODULE_DEFINITIONS = [
    (
        1,
        "Module 1: Foundations & Discipline",
        "Constrained systems prelude, C history and tools, best practices, error taxonomy, assertions, logging, unit testing, and hardware diagnostics milestone.",
        [
            ("intro.html", False, 45),
            ("topic_01.html", False, 45),
            ("topic_02.html", False, 45),
            ("topic_03.html", False, 45),
            ("topic_04.html", False, 45),
            ("topic_05.html", False, 45),
            ("project_01.html", True, 120),
        ]
    ),
    (
        2,
        "Module 2: Toolchains & Binaries",
        "The complete compilation pipeline, GCC cross-compilers, binary utilities (objdump, size, nm, GDB), Make and CMake, Git workflows, and linker script milestone.",
        [
            ("topic_06.html", False, 45),
            ("topic_07.html", False, 45),
            ("topic_08.html", False, 45),
            ("topic_09.html", False, 45),
            ("topic_10.html", False, 45),
            ("project_02.html", True, 120),
        ]
    ),
    (
        3,
        "Module 3: Reactive & Event-Driven Systems",
        "Event loop design, polling versus interrupts, asynchronous hardware callbacks, software timers, non-blocking firmware execution, and ring buffer milestone.",
        [
            ("topic_11.html", False, 45),
            ("topic_12.html", False, 45),
            ("topic_13.html", False, 45),
            ("topic_14.html", False, 45),
            ("project_03.html", True, 120),
        ]
    ),
    (
        4,
        "Module 4: Standards & State Machines",
        "Firmware style conventions, defensive programming patterns, Doxygen documentation, MISRA-C safety guidelines, finite state machines, state transition tables, and defensive controller milestone.",
        [
            ("topic_15.html", False, 45),
            ("topic_16.html", False, 45),
            ("topic_17.html", False, 45),
            ("topic_18.html", False, 45),
            ("topic_19.html", False, 45),
            ("topic_20.html", False, 45),
            ("project_04.html", True, 120),
        ]
    ),
    (
        5,
        "Module 5: Architecture & Integration",
        "Modular header and source decoupling, hardware abstraction interfaces, reusable component libraries, Application/Driver/HAL/BSP layering, and integrated production firmware capstone.",
        [
            ("topic_21.html", False, 45),
            ("topic_22.html", False, 45),
            ("topic_23.html", False, 45),
            ("topic_24.html", False, 45),
            ("topic_25.html", False, 45),
            ("project_05.html", True, 120),
        ]
    ),
    (
        6,
        "Module 6: Hardware & Engineering Reference Compendium",
        "Comprehensive hardware reference compendium: Silicon architectures (MCU vs MPU), sensors and transducers, actuators and power drivers, 20 industrial hardware architectures, and protocol standards.",
        [
            ("reference.html", False, 60),
            ("ref_sensors.html", False, 45),
            ("ref_actuators.html", False, 45),
            ("ref_silicon.html", False, 45),
            ("ref_devices.html", False, 60),
            ("ref_standards.html", False, 45),
        ]
    ),
    (
        7,
        "Module 7: Interactive Lab & Capstone",
        "The complete STM32 firmware execution journey: from C source compilation and linker mapping down to reset vectors, SRAM initialization, register manipulation, and interactive hardware simulation.",
        [
            ("stm32-firmware-journey.html", True, 180),
        ]
    ),
]


class Command(BaseCommand):
    help = "Seeds the comprehensive 38-lesson Embedded C Programming course from HTML materials into the LMS database."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dir',
            type=str,
            default=DEFAULT_COURSE_DIR,
            help="Directory path containing Embedded C Programming HTML files"
        )
        parser.add_argument(
            '--enroll-all',
            action='store_true',
            default=True,
            help="Automatically enroll all active LMS cohort users"
        )

    def handle(self, *args, **options):
        directory_path = options['dir']
        self.stdout.write(self.style.NOTICE(f"Starting Embedded C Programming Course Ingestion from: {directory_path}"))

        if not os.path.exists(directory_path) or not os.path.isdir(directory_path):
            self.stderr.write(self.style.ERROR(f"Directory '{directory_path}' does not exist or is not a directory."))
            return

        # 1. Create or Update Course
        course, created = Course.objects.update_or_create(
            code="EMBEDDED-C-2026",
            defaults={
                'title': "Embedded C Programming",
                'slug': "embedded-c-programming",
                'short_description': "From zero to bare-metal C, toolchains & linkers, reactive event-driven firmware, state machines, MISRA-C safety, and modern layered architectures.",
                'description': (
                    "A rigorous, 38-lesson engineering curriculum in Embedded C Programming designed for constrained microcontrollers. "
                    "Master constrained system fundamentals, bitwise manipulation, defensive C, cross-compilation toolchains (GCC, Make, CMake, GDB), "
                    "linker scripts (.ld), binary utilities (objdump, size, nm), reactive event-driven architectures, state machines, MISRA-C safety compliance, "
                    "modular HAL/BSP layering, hardware reference compendiums, and hands-on STM32 execution."
                ),
                'category': "Embedded Systems & IoT",
                'difficulty_level': "Intermediate to Advanced",
                'status': "PUBLISHED",
                'thumbnail': "embedded_c.svg",
                'is_active': True,
            }
        )
        course_action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{course_action} Course: [{course.code}] {course.title}"))

        # 2. Instructors Setup
        lead_instructor = (
            LMSUser.objects.filter(email='kamal@aptcomputinglabs.com').first()
            or LMSUser.objects.filter(role__in=['ADMIN', 'MANAGER', 'MENTOR']).first()
        )
        if lead_instructor:
            CourseInstructor.objects.update_or_create(
                course=course,
                instructor=lead_instructor,
                defaults={'role': 'LEAD', 'is_primary': True, 'is_active': True}
            )
            self.stdout.write(self.style.SUCCESS(f"Assigned Lead Instructor: {lead_instructor.full_name} ({lead_instructor.email})"))

        # 3. Create or Update Cohort Batch
        batch, b_created = Batch.objects.update_or_create(
            code="EMBEDDED-C-2026-B1",
            defaults={
                'name': "Embedded C Programming Cohort 2026",
                'course': course,
                'status': "ONGOING",
                'schedule': "Tue, Thu, Sat @ 19:00 - 21:00 IST",
                'schedule_days': "Tue, Thu, Sat",
                'schedule_time': "19:00 - 21:00",
                'start_date': date(2026, 9, 1),
                'end_date': date(2026, 11, 30),
                'description': "Flagship cohort for Embedded C Programming: From Zero to Bare-Metal & Modern Architecture.",
                'is_active': True,
            }
        )
        batch_action = "Created" if b_created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{batch_action} Batch: [{batch.code}] {batch.name}"))

        if lead_instructor:
            batch.mentors.add(lead_instructor)

        # 4. Ingest Curriculum Modules & Lessons
        global_lesson_order = 0
        lessons_created = 0
        lessons_updated = 0
        total_mcqs = 0

        for mod_order, mod_title, mod_desc, lesson_items in MODULE_DEFINITIONS:
            module, _ = Module.objects.update_or_create(
                course=course,
                order=mod_order,
                defaults={
                    'title': mod_title,
                    'description': mod_desc,
                    'is_active': True,
                }
            )
            self.stdout.write(f"\n  • Module {mod_order}: {mod_title} ({len(lesson_items)} lessons)")

            for file_name, is_lab, duration_mins in lesson_items:
                global_lesson_order += 1
                file_path = os.path.join(directory_path, file_name)

                if not os.path.exists(file_path):
                    self.stderr.write(self.style.WARNING(f"    File not found: {file_path}, skipping..."))
                    continue

                with open(file_path, 'r', encoding='utf-8', errors='replace') as fp:
                    raw_html = fp.read()

                soup = BeautifulSoup(raw_html, 'html.parser')

                # Extract Title
                title = ''
                title_tag = soup.find('title')
                h1_tag = soup.find('h1')

                if title_tag and title_tag.string:
                    title = title_tag.string.strip()
                elif h1_tag:
                    title = h1_tag.get_text().strip()
                else:
                    title = file_name.replace('.html', '').replace('_', ' ').title()

                # Clean Title formatting (strip suffix " - Embedded C Programming")
                title = re.sub(r'\s*-\s*Embedded C Programming.*$', '', title, flags=re.I).strip()

                # Extract Content
                if file_name == 'stm32-firmware-journey.html':
                    # Special handling for STM32 interactive lab: keep inline styles and interactive script
                    main_tag = soup.find('main', class_=re.compile(r'content-area', re.I)) or soup.find('main') or soup.find('body')
                    style_tag = soup.find('style')
                    script_tag = soup.find('script', src=None)  # inline script

                    content_parts = []
                    if style_tag:
                        content_parts.append(str(style_tag))
                    if main_tag:
                        # Decompose only theme toggle button which is outside our LMS theme
                        theme_btn = main_tag.find('button', id='theme-btn')
                        if theme_btn:
                            theme_btn.decompose()
                        content_parts.append(str(main_tag))
                    else:
                        content_parts.append(raw_html)

                    if script_tag:
                        content_parts.append(str(script_tag))

                    lesson_content = "\n".join(content_parts)
                else:
                    article_tag = (
                        soup.find('article', class_=re.compile(r'book-page|content', re.I))
                        or soup.find('article')
                        or soup.find('main')
                    )

                    if article_tag:
                        # Remove redundant navigation and raw submit buttons (LMS initLessonMCQs manages submit)
                        for nav_tag in article_tag.find_all(['nav', 'header', 'noscript']):
                            nav_tag.decompose()
                        for btn in article_tag.find_all('button', class_='mcq-submit'):
                            btn.decompose()
                        lesson_content = str(article_tag)
                    else:
                        lesson_content = raw_html

                # Remap local images to static folder
                lesson_content = re.sub(
                    r'src=["\'](?:\.?/)?images/',
                    'src="/static/img/courses/embedded-c/',
                    lesson_content
                )

                # Count MCQs in this chapter
                mcq_count = lesson_content.count('class="mcq-container"') + lesson_content.count("class='mcq-container'")
                total_mcqs += mcq_count

                lesson_type = 'LAB' if is_lab else 'ARTICLE'

                lesson, l_created = Lesson.objects.update_or_create(
                    module=module,
                    order=global_lesson_order,
                    defaults={
                        'title': title,
                        'lesson_type': lesson_type,
                        'duration_minutes': duration_mins,
                        'content': lesson_content,
                        'is_required': True,
                        'is_active': True,
                    }
                )

                if l_created:
                    lessons_created += 1
                else:
                    lessons_updated += 1

                # Register Batch Material
                BatchMaterial.objects.update_or_create(
                    batch=batch,
                    title=f"{title} (Course Material)",
                    defaults={
                        'material_type': 'DOCUMENT',
                        'description': f"Official curriculum readings, diagrams, and labs for {title}.",
                        'external_url': f"file://{file_path}",
                        'is_active': True,
                    }
                )

                self.stdout.write(f"    [{global_lesson_order:02d}] {title} ({lesson_type}, {duration_mins}m, {mcq_count} MCQs)")

        # 5. User Enrollments
        if options['enroll_all']:
            users = LMSUser.objects.filter(is_active=True)
            enrolled_count = 0
            for u in users:
                Enrollment.objects.get_or_create(
                    external_user_id=u.external_user_id,
                    course=course,
                    defaults={'status': 'ACTIVE', 'progress_percent': 0}
                )
                batch.students.add(u)
                enrolled_count += 1

            course.enrolled_count = Enrollment.objects.filter(course=course).count()
            course.save(update_fields=['enrolled_count'])
            self.stdout.write(self.style.SUCCESS(f"\nEnrolled {enrolled_count} cohort learners into the course & batch."))

        self.stdout.write(self.style.SUCCESS("\n" + "=" * 65))
        self.stdout.write(self.style.SUCCESS("Embedded C Programming Course Successfully Ingested!"))
        self.stdout.write(self.style.SUCCESS(f"Course: {course.title} ({course.code})"))
        self.stdout.write(self.style.SUCCESS(f"Modules: {course.modules.count()}"))
        self.stdout.write(self.style.SUCCESS(f"Lessons Created: {lessons_created}, Updated: {lessons_updated} (Total: {Lesson.objects.filter(module__course=course).count()})"))
        self.stdout.write(self.style.SUCCESS(f"Total Interactive MCQs: {total_mcqs}"))
        self.stdout.write(self.style.SUCCESS(f"Enrolled Learners: {course.enrolled_count}"))
        self.stdout.write(self.style.SUCCESS("=" * 65))
