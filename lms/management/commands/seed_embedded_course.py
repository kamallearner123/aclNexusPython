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

DEFAULT_COURSE_DIR = "/Users/kamalmukiri/Documents/1.GitHub/acl-agenctic-ai-book/AgenticAIBook/Embedded Systems"

MODULE_DEFINITIONS = [
    (
        1,
        (1, 8),
        "Module 1: Embedded C Foundations & Hardware Fundamentals",
        "Bare-metal C programming, memory architectures, register manipulation, GPIO, interrupts, timers, ADC/DAC, and communication protocols."
    ),
    (
        2,
        (9, 16),
        "Module 2: RTOS, Peripherals & Communication Protocols",
        "FreeRTOS fundamentals, task scheduling, synchronization primitives, DMA, automotive CAN bus, USB/wireless, bootloaders, and RTOS sensor hub capstone."
    ),
    (
        3,
        (17, 24),
        "Module 3: Advanced Topics, Safety, Debugging & Capstone",
        "Low-power system design, Flash/EEPROM/FatFS, MISRA-C safety-critical firmware, JTAG/SWD debugging, unit testing with Unity/CMock, embedded Linux, and automotive ECU grand capstone."
    ),
]

LAB_DAYS = {8, 16, 23, 24}


class Command(BaseCommand):
    help = "Seeds the 24-day Embedded Systems Engineering course from HTML materials into the LMS database."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dir',
            type=str,
            default=DEFAULT_COURSE_DIR,
            help="Directory path containing Embedded Systems day_*.html files"
        )
        parser.add_argument(
            '--enroll-all',
            action='store_true',
            default=True,
            help="Automatically enroll all active LMS cohort users"
        )

    def handle(self, *args, **options):
        directory_path = options['dir']
        self.stdout.write(self.style.NOTICE(f"Starting Embedded Systems Course Ingestion from: {directory_path}"))

        if not os.path.exists(directory_path) or not os.path.isdir(directory_path):
            self.stderr.write(self.style.ERROR(f"Directory '{directory_path}' does not exist or is not a directory."))
            return

        # 1. Create or Update Course
        course, created = Course.objects.update_or_create(
            code="EMBEDDED-SYS-2026",
            defaults={
                'title': "Embedded Systems Engineering",
                'slug': "embedded-systems",
                'short_description': "Master bare-metal C, ARM Cortex-M architecture, FreeRTOS multitasking, hardware peripherals, and safety-critical firmware.",
                'description': (
                    "A rigorous, 24-day engineering blueprint for designing, testing, and shipping real embedded systems. "
                    "Covers bare-metal C, ARM Cortex-M memory architectures, peripheral control (GPIO, Timers, NVIC, ADC/DAC), "
                    "serial and automotive protocols (UART, SPI, I2C, CAN Bus), FreeRTOS real-time kernels, DMA, bootloaders, "
                    "low-power modes, Flash/FatFS, MISRA-C safety compliance, JTAG debugging, unit testing with Unity/CMock, "
                    "embedded Linux, and automotive diagnostics."
                ),
                'category': "Embedded Systems & IoT",
                'difficulty_level': "Intermediate to Advanced",
                'status': "PUBLISHED",
                'thumbnail': "embedded.svg",
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

        # 3. Create or Update Syllabus Modules
        modules_by_day = {}
        for mod_order, (start_d, end_d), title, desc in MODULE_DEFINITIONS:
            module, _ = Module.objects.update_or_create(
                course=course,
                order=mod_order,
                defaults={
                    'title': title,
                    'description': desc,
                    'is_active': True,
                }
            )
            for d in range(start_d, end_d + 1):
                modules_by_day[d] = module
            self.stdout.write(f"  • Module {mod_order}: {title} (Days {start_d}–{end_d})")

        # 4. Create or Update Cohort Batch
        batch, b_created = Batch.objects.update_or_create(
            code="EMBEDDED-2026-B1",
            defaults={
                'name': "Embedded Systems Engineering Cohort 2026",
                'course': course,
                'status': "ONGOING",
                'schedule': "Mon, Wed, Fri @ 19:00 - 21:00 IST",
                'schedule_days': "Mon, Wed, Fri",
                'schedule_time': "19:00 - 21:00",
                'start_date': date(2026, 9, 1),
                'end_date': date(2026, 11, 30),
                'description': "Flagship cohort for Embedded Systems Engineering: Learn by Examples.",
                'is_active': True,
            }
        )
        batch_action = "Created" if b_created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{batch_action} Batch: [{batch.code}] {batch.name}"))

        if lead_instructor:
            batch.mentors.add(lead_instructor)

        # 5. Ingest Day HTML Files
        day_files = sorted([
            f for f in os.listdir(directory_path)
            if re.match(r'^day_\d+\.html$', f, re.I)
        ])

        if not day_files:
            self.stderr.write(self.style.ERROR(f"No day_*.html files found in '{directory_path}'."))
            return

        self.stdout.write(self.style.NOTICE(f"Ingesting {len(day_files)} chapter files..."))

        lessons_created = 0
        lessons_updated = 0
        total_mcqs = 0

        for file_name in day_files:
            file_path = os.path.join(directory_path, file_name)
            day_match = re.search(r'day_(\d+)', file_name, re.I)
            day_num = int(day_match.group(1)) if day_match else (lessons_created + 1)

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
                title = f"Day {day_num}: Embedded Systems Chapter {day_num}"

            # Clean Title format: Day X: Topic Title
            title = re.sub(r'\s*-\s*Embedded Systems.*$', '', title, flags=re.I).strip()
            if not re.match(r'^Day\s+\d+:', title, re.I):
                title = f"Day {day_num}: {title}"

            # Extract Article Content
            article_tag = (
                soup.find('article', class_=re.compile(r'book-page|content', re.I))
                or soup.find('article')
                or soup.find('main')
            )

            if article_tag:
                # Remove redundant navigational and duplicate script elements
                # Keep MCQs, SVGs, code blocks, tables, callouts intact
                for tag in article_tag.find_all(['nav', 'header', 'noscript', 'button']):
                    # If button has class mcq-submit, decompose it as lesson_view.html provides the unified UI
                    tag.decompose()
                lesson_content = str(article_tag)
            else:
                lesson_content = raw_html

            # Count MCQs in this chapter
            mcq_count = lesson_content.count('class="mcq-container"') + lesson_content.count("class='mcq-container'")
            total_mcqs += mcq_count

            # Determine lesson type & duration
            is_lab = day_num in LAB_DAYS or any(kw in title.lower() for kw in ['capstone', 'milestone', 'project', 'lab'])
            lesson_type = 'LAB' if is_lab else 'ARTICLE'
            duration_minutes = 120 if is_lab else 45

            target_module = modules_by_day.get(day_num)
            if not target_module:
                target_module = Module.objects.filter(course=course).first()

            lesson, l_created = Lesson.objects.update_or_create(
                module=target_module,
                order=day_num,
                defaults={
                    'title': title,
                    'lesson_type': lesson_type,
                    'duration_minutes': duration_minutes,
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
                title=f"{title} (Lesson Material)",
                defaults={
                    'material_type': 'DOCUMENT',
                    'description': f"Official curriculum readings, diagrams, and labs for Day {day_num}.",
                    'external_url': f"file://{file_path}",
                    'is_active': True,
                }
            )

            self.stdout.write(f"  [Day {day_num:02d}] {title} ({lesson_type}, {mcq_count} MCQs)")

        # 6. User Enrollments
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
            self.stdout.write(self.style.SUCCESS(f"Enrolled {enrolled_count} cohort learners into the course & batch."))

        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))
        self.stdout.write(self.style.SUCCESS("Embedded Systems Course Successfully Ingested!"))
        self.stdout.write(self.style.SUCCESS(f"Course: {course.title} ({course.code})"))
        self.stdout.write(self.style.SUCCESS(f"Modules: {course.modules.count()}"))
        self.stdout.write(self.style.SUCCESS(f"Lessons Created: {lessons_created}, Updated: {lessons_updated} (Total: {Lesson.objects.filter(module__course=course).count()})"))
        self.stdout.write(self.style.SUCCESS(f"Total Interactive MCQs: {total_mcqs}"))
        self.stdout.write(self.style.SUCCESS(f"Enrolled Learners: {course.enrolled_count}"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
