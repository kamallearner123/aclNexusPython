from datetime import timedelta, time
from django.test import TestCase, Client
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.urls import reverse

from lms.models import (
    LMSUser,
    Course,
    Module,
    Lesson,
    Enrollment,
    LiveClass,
    Assignment,
    AssignmentSubmission,
    Certificate,
    CourseInstructor,
    Batch,
    BatchSession,
    BatchMaterial,
    StudentPayment,
)
from lms.router import LMSDatabaseRouter
from lms.services import (
    sync_lms_user,
    mark_lesson_completed,
    calculate_course_progress,
    submit_assignment,
)
from lms.selectors import get_next_two_sessions

User = get_user_model()


from core.models import Role


class LMSArchitectureTests(TestCase):
    databases = {'default', 'lms'}

    def setUp(self):
        self.client = Client()
        self.router = LMSDatabaseRouter()

        # Core users
        self.admin_user = User.objects.create_superuser(
            id=101,
            email='admin_test@example.com',
            password='Password@123',
            first_name='Admin',
            last_name='User'
        )
        self.student_user = User.objects.create_user(
            id=102,
            email='student_test@example.com',
            password='Password@123',
            first_name='Student',
            last_name='User'
        )

        # LMS users
        self.admin_lms = sync_lms_user(self.admin_user, role='ADMIN')
        self.student_lms = sync_lms_user(self.student_user, role='STUDENT')

        # Sample Course
        self.course = Course.objects.create(
            code='TEST-AI-101',
            title='Test Agentic Systems',
            slug='test-agentic-systems',
            short_description='Testing course architecture',
            description='Detailed test curriculum',
            category='Artificial Intelligence',
            difficulty_level='Intermediate',
            status='PUBLISHED'
        )

    def test_database_isolation(self):
        """
        Verify LMS tables are routed strictly to 'lms' database and core tables to 'default'.
        """
        # Test routing rules
        self.assertEqual(self.router.db_for_read(LMSUser), 'lms')
        self.assertEqual(self.router.db_for_write(LMSUser), 'lms')
        self.assertEqual(self.router.db_for_read(Course), 'lms')
        self.assertEqual(self.router.db_for_write(Course), 'lms')

        self.assertEqual(self.router.db_for_read(User), 'default')
        self.assertEqual(self.router.db_for_write(User), 'default')

        # Test migration isolation
        self.assertTrue(self.router.allow_migrate('lms', 'lms'))
        self.assertFalse(self.router.allow_migrate('default', 'lms'))
        self.assertTrue(self.router.allow_migrate('default', 'core'))
        self.assertFalse(self.router.allow_migrate('lms', 'core'))

    def test_cross_database_identity(self):
        """
        Verify LMSUser references core user via external_user_id without cross-db FK.
        """
        field = LMSUser._meta.get_field('external_user_id')
        self.assertFalse(field.is_relation, "external_user_id must not be a relational ForeignKey")
        self.assertEqual(field.get_internal_type(), 'PositiveBigIntegerField')
        self.assertTrue(field.unique)

        # Ensure synchronization works cleanly
        self.assertEqual(self.student_lms.external_user_id, self.student_user.id)
        self.assertEqual(self.student_lms.email, self.student_user.email)

    def test_assignment_submission_uniqueness(self):
        """
        Verify student cannot create duplicate submission records for the same assignment.
        Submitting updates the single record and resets status.
        """
        assignment = Assignment.objects.create(
            course=self.course,
            title='Test Milestone 1',
            description='Build an autonomous agent',
            max_score=100,
            status='ACTIVE',
            order=1
        )

        # First submission
        sub1 = submit_assignment(
            assignment=assignment,
            external_user_id=self.student_user.id,
            submission_url='https://github.com/student/agent-v1',
            submission_text='Initial solution'
        )
        self.assertEqual(sub1.status, 'SUBMITTED')
        self.assertEqual(AssignmentSubmission.objects.filter(assignment=assignment, external_user_id=self.student_user.id).count(), 1)

        # Resubmission updates the single existing record
        sub2 = submit_assignment(
            assignment=assignment,
            external_user_id=self.student_user.id,
            submission_url='https://github.com/student/agent-v2',
            submission_text='Updated revision'
        )
        self.assertEqual(sub2.id, sub1.id)
        self.assertEqual(sub2.submission_url, 'https://github.com/student/agent-v2')
        self.assertEqual(AssignmentSubmission.objects.filter(assignment=assignment, external_user_id=self.student_user.id).count(), 1)

        # Attempting raw duplicate insertion violates database constraint
        with self.assertRaises(IntegrityError):
            AssignmentSubmission.objects.create(
                assignment=assignment,
                external_user_id=self.student_user.id,
                submission_url='https://github.com/student/agent-duplicate'
            )

    def test_progress_calculation(self):
        """
        Verify course progress exactly matches required lesson completion ratio:
        Course Progress (%) = round((Completed Required Lessons / Total Required Lessons) * 100)
        """
        module = Module.objects.create(course=self.course, title='Module 1', order=1)
        lesson1 = Lesson.objects.create(module=module, title='Lesson 1', order=1, is_required=True)
        lesson2 = Lesson.objects.create(module=module, title='Lesson 2', order=2, is_required=True)
        lesson3 = Lesson.objects.create(module=module, title='Lesson 3', order=3, is_required=True)
        lesson4 = Lesson.objects.create(module=module, title='Lesson 4', order=4, is_required=True)

        enrollment = Enrollment.objects.create(
            external_user_id=self.student_user.id,
            course=self.course,
            status='ACTIVE',
            progress_percent=0
        )

        # 0 completed
        self.assertEqual(calculate_course_progress(enrollment), 0)

        # 1 completed -> 25%
        mark_lesson_completed(enrollment, lesson1)
        enrollment.refresh_from_db()
        self.assertEqual(enrollment.progress_percent, 25)

        # 2 completed -> 50%
        mark_lesson_completed(enrollment, lesson2)
        enrollment.refresh_from_db()
        self.assertEqual(enrollment.progress_percent, 50)

        # 3 completed -> 75%
        mark_lesson_completed(enrollment, lesson3)
        enrollment.refresh_from_db()
        self.assertEqual(enrollment.progress_percent, 75)

        # 4 completed -> 100%, status COMPLETED, Certificate issued
        mark_lesson_completed(enrollment, lesson4)
        enrollment.refresh_from_db()
        self.assertEqual(enrollment.progress_percent, 100)
        self.assertEqual(enrollment.status, 'COMPLETED')
        self.assertTrue(Certificate.objects.filter(enrollment=enrollment).exists())

    def test_live_class_next_two_query(self):
        """
        Verify only upcoming sessions are queried, ordered by date and capped at 2.
        """
        now = timezone.now()
        yesterday = (now - timedelta(days=1)).date()
        date_1 = (now + timedelta(days=1)).date()
        date_2 = (now + timedelta(days=2)).date()
        date_3 = (now + timedelta(days=4)).date()

        # Past class
        LiveClass.objects.create(
            title='Past Class',
            course=self.course,
            instructor=self.admin_lms,
            scheduled_date=yesterday,
            start_time=time(19, 0),
            end_time=time(20, 30),
            meeting_url='https://meet.google.com/past',
            status='COMPLETED'
        )

        # 3 Upcoming classes
        s1 = LiveClass.objects.create(
            title='Session 1 Upcoming',
            course=self.course,
            instructor=self.admin_lms,
            scheduled_date=date_1,
            start_time=time(19, 0),
            end_time=time(20, 30),
            meeting_url='https://meet.google.com/session-1',
            status='UPCOMING'
        )
        s2 = LiveClass.objects.create(
            title='Session 2 Upcoming',
            course=self.course,
            instructor=self.admin_lms,
            scheduled_date=date_2,
            start_time=time(19, 0),
            end_time=time(20, 30),
            meeting_url='https://meet.google.com/session-2',
            status='UPCOMING'
        )
        LiveClass.objects.create(
            title='Session 3 Upcoming',
            course=self.course,
            instructor=self.admin_lms,
            scheduled_date=date_3,
            start_time=time(19, 0),
            end_time=time(20, 30),
            meeting_url='https://meet.google.com/session-3',
            status='UPCOMING'
        )

        next_two = get_next_two_sessions(self.course)
        self.assertEqual(len(next_two), 2)
        self.assertEqual(next_two[0].id, s1.id)
        self.assertEqual(next_two[1].id, s2.id)

    def test_server_side_rbac_enforcement(self):
        """
        Verify non-admin/non-mentor accounts receive 403 Forbidden on admin-hub,
        while authorized accounts can view the admin hub.
        """
        admin_hub_url = reverse('lms:admin_hub')

        # Student login -> 403 Forbidden
        self.client.force_login(self.student_user)
        resp_student = self.client.get(admin_hub_url)
        self.assertEqual(resp_student.status_code, 403)

        # Admin login -> 200 OK
        self.client.force_login(self.admin_user)
        resp_admin = self.client.get(admin_hub_url)
        self.assertEqual(resp_admin.status_code, 200)

    def test_domain_isolation_middleware(self):
        """
        Verify strict domain isolation in both directions:
        1. LMS Students cannot access PMS routes (/dashboard, /projects, /tasks, /issues, etc.)
        2. PMS Members cannot access LMS routes (/lms, /lms/courses, etc.)
        3. Superusers have access to both domains.
        """
        # Create a pure PMS Developer user
        dev_role, _ = Role.objects.get_or_create(name='Developer')
        pms_user = User.objects.create_user(
            id=103,
            email='pms_dev@example.com',
            password='Password@123',
            first_name='PMS',
            last_name='Developer'
        )
        pms_user.roles.add(dev_role)
        sync_lms_user(pms_user, role='USER')

        # 1. Test PMS User access
        self.client.force_login(pms_user)

        # PMS User accessing PMS Dashboard is allowed (returns 200 or redirect to role dashboard)
        resp = self.client.get('/dashboard/', follow=False)
        self.assertIn(resp.status_code, [200, 302])
        if resp.status_code == 302:
            self.assertIn('dashboard', resp.url)

        # PMS User attempting to access LMS is strictly blocked and redirected to /dashboard/
        resp = self.client.get('/lms/', follow=False)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, '/dashboard/')

        resp = self.client.get('/lms/courses/', follow=False)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, '/dashboard/')

        # 2. Test LMS Student access
        self.client.force_login(self.student_user)

        # LMS Student accessing LMS is allowed
        resp = self.client.get('/lms/', follow=False)
        self.assertEqual(resp.status_code, 200)

        # LMS Student attempting to access PMS routes is strictly blocked and redirected to /lms/
        resp = self.client.get('/dashboard/', follow=False)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, '/lms/')

        resp = self.client.get('/projects/', follow=False)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, '/lms/')

        resp = self.client.get('/tasks/my-tasks/', follow=False)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, '/lms/')

        # 3. Test Admin user access
        self.client.force_login(self.admin_user)

        # Admin can access LMS
        resp = self.client.get('/lms/', follow=False)
        self.assertEqual(resp.status_code, 200)

        # Admin can access PMS Dashboard
        resp = self.client.get('/dashboard/', follow=False)
        self.assertIn(resp.status_code, [200, 302])

    def test_admin_see_running_courses_and_stats(self):
        """
        Requirement 1: Admin should be able to see running courses and their stats.
        """
        from lms.selectors import get_courses_with_stats

        # Enroll student in test course
        Enrollment.objects.create(
            external_user_id=self.student_user.id,
            course=self.course,
            status='ACTIVE',
            progress_percent=45
        )

        stats = get_courses_with_stats()
        self.assertTrue(len(stats) >= 1)
        course_stat = next(s for s in stats if s['course'].id == self.course.id)

        self.assertTrue(course_stat['is_running'])
        self.assertEqual(course_stat['total_enrolled'], 1)
        self.assertEqual(course_stat['avg_progress'], 45)
        self.assertEqual(len(course_stat['enrolled_students']), 1)
        self.assertEqual(course_stat['enrolled_students'][0]['external_user_id'], self.student_user.id)

        # Verify Admin Hub renders with stats
        self.client.force_login(self.admin_user)
        resp = self.client.get('/lms/admin-hub/?tab=courses')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('courses_stats', resp.context)
        self.assertContains(resp, self.course.code)
        self.assertContains(resp, self.course.title)

    def test_admin_add_student_mentor_manager(self):
        """
        Requirement 2: Admin should be able to add students, mentors, managers.
        """
        self.client.force_login(self.admin_user)

        # 1. Add a Student
        resp_student = self.client.post('/lms/admin-hub/cohort-user/add/', {
            'email': 'new_student@example.com',
            'first_name': 'New',
            'last_name': 'Student',
            'role': 'STUDENT',
            'password': '', # test default password
            'specialization': 'Robotics AI',
            'phone': '1234567890',
            'bio': 'Aspiring AI Engineer',
        }, follow=True)
        self.assertEqual(resp_student.status_code, 200)

        new_student_core = User.objects.filter(email='new_student@example.com').first()
        self.assertIsNotNone(new_student_core)
        self.assertTrue(new_student_core.check_password('AclMission@123'))
        self.assertFalse(new_student_core.is_staff)
        self.assertEqual(new_student_core.roles.count(), 0) # Zero PMS roles

        new_student_lms = LMSUser.objects.filter(external_user_id=new_student_core.id).first()
        self.assertIsNotNone(new_student_lms)
        self.assertEqual(new_student_lms.role, 'STUDENT')
        self.assertEqual(new_student_lms.specialization, 'Robotics AI')

        # 2. Add a Mentor (Teacher)
        resp_mentor = self.client.post('/lms/admin-hub/cohort-user/add/', {
            'email': 'new_mentor@example.com',
            'first_name': 'Dr.',
            'last_name': 'Mentor',
            'role': 'MENTOR',
            'password': 'CustomPassword@123',
            'specialization': 'Deep Learning',
        }, follow=True)
        self.assertEqual(resp_mentor.status_code, 200)

        new_mentor_core = User.objects.filter(email='new_mentor@example.com').first()
        self.assertIsNotNone(new_mentor_core)
        self.assertTrue(new_mentor_core.check_password('CustomPassword@123'))

        new_mentor_lms = LMSUser.objects.filter(external_user_id=new_mentor_core.id).first()
        self.assertIsNotNone(new_mentor_lms)
        self.assertEqual(new_mentor_lms.role, 'MENTOR')

        # 3. Add a Program Manager
        resp_manager = self.client.post('/lms/admin-hub/cohort-user/add/', {
            'email': 'new_manager@example.com',
            'first_name': 'Academic',
            'last_name': 'Manager',
            'role': 'MANAGER',
            'specialization': 'Curriculum Operations',
        }, follow=True)
        self.assertEqual(resp_manager.status_code, 200)

        new_mgr_core = User.objects.filter(email='new_manager@example.com').first()
        self.assertIsNotNone(new_mgr_core)
        new_mgr_lms = LMSUser.objects.filter(external_user_id=new_mgr_core.id).first()
        self.assertIsNotNone(new_mgr_lms)
        self.assertEqual(new_mgr_lms.role, 'MANAGER')

    def test_admin_create_course_and_join_students(self):
        """
        Requirement 3: Admin should be able to create Courses and join students,
        so that students or teachers can see the courses.
        """
        self.client.force_login(self.admin_user)

        # 1. Create a Course with auto-enroll all students enabled
        resp_create = self.client.post('/lms/admin-hub/courses/create/', {
            'code': 'DL-2026',
            'title': 'Deep Learning & Neural Networks',
            'slug': 'deep-learning-neural-networks',
            'category': 'Machine Learning',
            'difficulty_level': 'Advanced',
            'status': 'PUBLISHED',
            'short_description': 'Advanced neural architectures and transformers.',
            'description': 'Comprehensive hands-on deep learning curriculum.',
            'lead_instructor': self.admin_lms.id,
            'enroll_all_students': True,
        }, follow=False)
        self.assertEqual(resp_create.status_code, 302)

        created_course = Course.objects.filter(code='DL-2026').first()
        self.assertIsNotNone(created_course)
        self.assertEqual(created_course.title, 'Deep Learning & Neural Networks')

        # Verify teacher is assigned as lead instructor
        instructor_record = CourseInstructor.objects.filter(course=created_course, instructor=self.admin_lms).first()
        self.assertIsNotNone(instructor_record)
        self.assertTrue(instructor_record.is_primary)

        # Verify students were automatically joined/enrolled
        enrollment = Enrollment.objects.filter(course=created_course, external_user_id=self.student_user.id).first()
        self.assertIsNotNone(enrollment)
        self.assertEqual(enrollment.status, 'ACTIVE')

        # 2. Verify student sees the new course on their dashboard
        self.client.force_login(self.student_user)
        student_dash = self.client.get('/lms/')
        self.assertEqual(student_dash.status_code, 200)
        self.assertContains(student_dash, 'DL-2026')
        self.assertContains(student_dash, 'Deep Learning')

        # 3. Verify teacher sees the course on their dashboard & course catalog
        self.client.force_login(self.admin_user)
        admin_dash = self.client.get('/lms/')
        self.assertEqual(admin_dash.status_code, 200)
        self.assertContains(admin_dash, 'DL-2026')

        catalog_resp = self.client.get('/lms/courses/')
        self.assertEqual(catalog_resp.status_code, 200)
        self.assertContains(catalog_resp, 'DL-2026')

        # 4. Test manual student join action (join single)
        extra_student = User.objects.create_user(
            id=109,
            email='extra_student@example.com',
            password='Password@123'
        )
        extra_lms = sync_lms_user(extra_student, role='STUDENT')

        resp_join = self.client.post('/lms/admin-hub/courses/join-students/', {
            'action': 'enroll_single',
            'course_id': created_course.id,
            'student_id': extra_lms.id,
        }, follow=False)
        self.assertEqual(resp_join.status_code, 302)

        self.assertTrue(
            Enrollment.objects.filter(course=created_course, external_user_id=extra_student.id).exists()
        )


class BatchSessionsMaterialsAdminNavigationTest(TestCase):
    databases = {'default', 'lms'}

    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            id=201,
            email='lms_admin@example.com',
            password='Password@123'
        )
        self.admin_lms = sync_lms_user(self.admin_user, role='ADMIN')

        self.student_user = User.objects.create_user(
            id=202,
            email='cohort_student@example.com',
            password='Password@123'
        )
        self.student_lms = sync_lms_user(self.student_user, role='STUDENT')

        self.mentor_user = User.objects.create_user(
            id=203,
            email='lead_mentor@example.com',
            password='Password@123'
        )
        self.mentor_lms = sync_lms_user(self.mentor_user, role='MENTOR')

        # Create a batch
        self.batch = Batch.objects.create(
            name='AI Agents & LLM Systems Cohort',
            code='AGENT-2026',
            status='ONGOING',
            description='Applied engineering cohort for generative AI and stateful agents.'
        )
        self.batch.students.add(self.student_lms)
        self.batch.mentors.add(self.mentor_lms)

    def test_admin_navigation_and_dashboard_tabs(self):
        """
        Verify that for LMS Admin:
        - Sidebar is structured into 4 domains: Academic, People, Operations, Administration
        - Academic domain contains Courses, Batches, Sessions, Materials, Assessments
        - People domain contains Students, Mentors
        - Operations domain contains Attendance, Payments, Reports
        - Administration domain contains Users & Roles, Settings, Audit Logs
        - Dashboard top tab bar contains all domain tabs
        - Landing Dashboard tab contains Banner, Consolidated + Create / Add dropdown, 7 actionable KPIs, and Operations Panel
        """
        self.client.force_login(self.admin_user)
        response = self.client.get('/lms/')
        self.assertEqual(response.status_code, 200)

        # Admin sidebar domain headers
        self.assertContains(response, 'Academic')
        self.assertContains(response, 'People')
        self.assertContains(response, 'Operations')
        self.assertContains(response, 'Administration')

        # Admin sidebar domain links
        self.assertContains(response, '?tab=courses')
        self.assertContains(response, '?tab=batches')
        self.assertContains(response, '?tab=sessions')
        self.assertContains(response, '?tab=materials')
        self.assertContains(response, '?tab=assessments')
        self.assertContains(response, '?tab=students')
        self.assertContains(response, '?tab=mentors')
        self.assertContains(response, '?tab=attendance')
        self.assertContains(response, '?tab=payments')
        self.assertContains(response, '?tab=reports')
        self.assertContains(response, '?tab=users')
        self.assertContains(response, '?tab=settings')
        self.assertContains(response, '?tab=audit')

        # Admin dashboard top tabs checks
        self.assertContains(response, 'id="tab-btn-dashboard"')
        self.assertContains(response, 'id="tab-btn-courses"')
        self.assertContains(response, 'id="tab-btn-batches"')
        self.assertContains(response, 'id="tab-btn-sessions"')
        self.assertContains(response, 'id="tab-btn-materials"')
        self.assertContains(response, 'id="tab-btn-assessments"')
        self.assertContains(response, 'id="tab-btn-students"')
        self.assertContains(response, 'id="tab-btn-mentors"')
        self.assertContains(response, 'id="tab-btn-attendance"')
        self.assertContains(response, 'id="tab-btn-payments"')
        self.assertContains(response, 'id="tab-btn-reports"')
        self.assertContains(response, 'id="tab-btn-users"')
        self.assertContains(response, 'id="tab-btn-settings"')
        self.assertContains(response, 'id="tab-btn-audit"')

        # Landing Dashboard tab contains Banner, Consolidated action dropdown & 7 Actionable KPI cards
        self.assertContains(response, 'LMS Academic Operations &amp; Batch Command')
        self.assertContains(response, '+ Create / Add')
        self.assertContains(response, 'Learner View')
        self.assertContains(response, 'id="tab-dashboard"')

        # Admin Operations Panel sections
        self.assertContains(response, 'Upcoming Live Sessions Schedule')
        self.assertContains(response, 'Learners Requiring Attention')
        self.assertContains(response, 'Active Cohorts &amp; Batches')
        self.assertContains(response, 'Tuition &amp; Fee Status')
        self.assertContains(response, 'Live Operations Activity')

    def test_student_navigation_retains_learning_tabs(self):
        """
        Verify that for non-admin students:
        - Sidebar contains: Learning, Dashboard, Courses & Syllabus, Live Classes, Assignments, Faculty Mentors, Tuition & Fees
        - Sidebar DOES NOT contain admin domains (Batches, Audit Logs, Administrator Command)
        """
        self.client.force_login(self.student_user)
        response = self.client.get('/lms/')
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, 'Learning')
        self.assertContains(response, 'Courses & Syllabus')
        self.assertContains(response, 'Live Classes')
        self.assertContains(response, 'Assignments')
        self.assertContains(response, 'Faculty Mentors')
        self.assertNotContains(response, '?tab=batches')
        self.assertNotContains(response, '?tab=audit')
        self.assertNotContains(response, 'Administrator Command')

    def test_batch_sessions_and_materials_management(self):
        """
        Verify scheduling a live session with meeting link and adding materials & attachments.
        """
        self.client.force_login(self.admin_user)

        # 1. Schedule a live session
        session_resp = self.client.post(f'/lms/batches/{self.batch.id}/sessions/add/', {
            'title': 'Session 1: Architectural Foundations & Tool Use',
            'meeting_link': 'https://meet.google.com/abc-defg-hij',
            'scheduled_date': '2026-09-20',
            'start_time': '18:00',
            'end_time': '20:00',
            'status': 'UPCOMING',
            'agenda': 'Introduction to tool calling and multi-agent coordination.',
            'instructor': self.mentor_lms.id,
            'next': f'/lms/batches/{self.batch.id}/'
        }, follow=False)
        self.assertEqual(session_resp.status_code, 302)

        session = BatchSession.objects.filter(batch=self.batch, title__contains='Tool Use').first()
        self.assertIsNotNone(session)
        self.assertEqual(session.meeting_link, 'https://meet.google.com/abc-defg-hij')

        # 2. Add material via batch endpoint
        mat_resp = self.client.post(f'/lms/batches/{self.batch.id}/materials/add/', {
            'title': 'Lab 1 Starter Repository',
            'material_type': 'CODE_REPO',
            'external_url': 'https://github.com/apt-computing-labs/agent-starter',
            'description': 'Clone this repository for Session 1 hands-on lab.',
            'next': f'/lms/batches/{self.batch.id}/'
        }, follow=False)
        self.assertEqual(mat_resp.status_code, 302)

        material = BatchMaterial.objects.filter(batch=self.batch, title__contains='Starter Repository').first()
        self.assertIsNotNone(material)
        self.assertEqual(material.material_type, 'CODE_REPO')

        # 3. Add general material via general endpoint
        mat_gen_resp = self.client.post('/lms/materials/add/', {
            'batch_id': self.batch.id,
            'title': 'System Architecture Slide Deck',
            'material_type': 'SLIDES',
            'external_url': 'https://drive.google.com/file/d/architecture-deck',
            'description': 'Presentation slides for cohort orientation.',
            'next': '/lms/?tab=materials'
        }, follow=False)
        self.assertEqual(mat_gen_resp.status_code, 302)

        slide_material = BatchMaterial.objects.filter(batch=self.batch, material_type='SLIDES').first()
        self.assertIsNotNone(slide_material)

        # 4. Verify batch detail page shows sessions and materials
        batch_detail = self.client.get(f'/lms/batches/{self.batch.id}/')
        self.assertEqual(batch_detail.status_code, 200)
        self.assertContains(batch_detail, 'https://meet.google.com/abc-defg-hij')
        self.assertContains(batch_detail, 'Lab 1 Starter Repository')
        self.assertContains(batch_detail, 'System Architecture Slide Deck')

        # 5. Verify materials tab in admin dashboard
        dash_materials = self.client.get('/lms/?tab=materials')
        self.assertEqual(dash_materials.status_code, 200)
        self.assertContains(dash_materials, 'Lab 1 Starter Repository')
        self.assertContains(dash_materials, 'System Architecture Slide Deck')

        # 6. Delete material
        del_resp = self.client.post(f'/lms/batches/materials/{material.id}/delete/', {
            'next': '/lms/?tab=materials'
        }, follow=False)
        self.assertEqual(del_resp.status_code, 302)
        self.assertFalse(BatchMaterial.objects.filter(id=material.id).exists())

    def test_general_schedule_session(self):
        """
        Verify general schedule live session endpoint (/lms/sessions/add/).
        """
        self.client.force_login(self.admin_user)
        resp = self.client.post('/lms/sessions/add/', {
            'batch_id': self.batch.id,
            'title': 'General Cohort Masterclass',
            'meeting_link': 'https://meet.google.com/xyz-uvwx-rst',
            'scheduled_date': '2026-09-25',
            'start_time': '10:00',
            'end_time': '12:00',
            'status': 'UPCOMING',
            'next': '/lms/?tab=sessions'
        }, follow=False)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, '/lms/?tab=sessions')

        session = BatchSession.objects.filter(batch=self.batch, title='General Cohort Masterclass').first()
        self.assertIsNotNone(session)
        self.assertEqual(session.meeting_link, 'https://meet.google.com/xyz-uvwx-rst')

    def test_create_course_from_admin_dashboard(self):
        """
        Verify course creation from admin dashboard modal redirecting to ?tab=courses.
        """
        self.client.force_login(self.admin_user)
        resp = self.client.post('/lms/admin-hub/courses/create/', {
            'code': 'CLOUD-2026',
            'title': 'Enterprise Cloud Architecture',
            'category': 'Cloud Infrastructure',
            'difficulty_level': 'Advanced',
            'status': 'PUBLISHED',
            'short_description': 'Enterprise scale cloud patterns',
            'description': 'Full cloud curriculum syllabus.',
            'enroll_all_students': True,
            'next': '/lms/?tab=courses'
        }, follow=False)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, '/lms/?tab=courses')

        course = Course.objects.filter(code='CLOUD-2026').first()
        self.assertIsNotNone(course)
        self.assertEqual(course.title, 'Enterprise Cloud Architecture')
        self.assertTrue(Enrollment.objects.filter(course=course, external_user_id=self.student_user.id).exists())

    def test_admin_kpis_and_operational_panel(self):
        """
        Verify get_admin_dashboard_data computes the 7 KPIs and flags students requiring attention.
        """
        from lms.selectors import get_admin_dashboard_data

        # Record a pending fee for the student
        StudentPayment.objects.create(
            student=self.student_lms,
            batch=self.batch,
            title='Cohort Tuition Fee',
            total_amount=25000.00,
            amount_paid=5000.00,
            payment_status='PARTIAL'
        )

        data = get_admin_dashboard_data()
        kpis = data.get('kpis', {})
        self.assertIn('active_courses', kpis)
        self.assertIn('active_students', kpis)
        self.assertIn('attendance_rate', kpis)
        self.assertIn('upcoming_sessions', kpis)
        self.assertIn('assessments', kpis)
        self.assertIn('completion_rate', kpis)
        self.assertIn('pending_actions', kpis)

        # Pending fee should reflect in pending actions and attention items
        self.assertEqual(kpis['pending_actions']['value'], '₹20,000')
        self.assertIn('1 Pending Due', kpis['pending_actions']['trend'])

        attention_items = data.get('students_requiring_attention', [])
        self.assertTrue(any(item['student'].id == self.student_lms.id for item in attention_items))
        due_item = next(item for item in attention_items if item['student'].id == self.student_lms.id)
        self.assertIn('Fee Due: ₹20,000', due_item['title'])


class BatchCreationAndScheduleTests(TestCase):
    databases = {'default', 'lms'}

    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            id=301,
            email='admin_batch_test@example.com',
            password='Password@123'
        )
        self.admin_lms = sync_lms_user(self.admin_user, role='ADMIN')

    def test_create_batch_with_mandatory_fields_and_schedule(self):
        """
        Verify creating batch with mandatory fields (Name, GitHub Path, GDrive Path),
        schedule (repetitive days), Zoom link, and auto session generation.
        """
        self.client.force_login(self.admin_user)
        payload = {
            'name': 'AI Engineering & Agents Cohort 2026',
            'code': 'BATCH-AI-2026',
            'github_path': 'https://github.com/apt-computing-labs/agent-systems',
            'gdrive_path': 'https://drive.google.com/drive/folders/cohort-2026-materials',
            'zoom_link': 'https://zoom.us/j/9876543210?pwd=test',
            'schedule_days': 'Mon, Wed, Fri',
            'schedule_time': '19:00 - 21:00 IST',
            'schedule': 'Every Mon, Wed, Fri from 19:00 to 21:00 IST',
            'status': 'ONGOING',
            'auto_generate_sessions': True,
            'next': '/lms/?tab=batches',
        }

        resp = self.client.post('/lms/batches/create/', payload, follow=False)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, '/lms/?tab=batches')

        batch = Batch.objects.filter(code='BATCH-AI-2026').first()
        self.assertIsNotNone(batch)
        self.assertEqual(batch.name, 'AI Engineering & Agents Cohort 2026')
        self.assertEqual(batch.github_path, 'https://github.com/apt-computing-labs/agent-systems')
        self.assertEqual(batch.gdrive_path, 'https://drive.google.com/drive/folders/cohort-2026-materials')
        self.assertEqual(batch.zoom_link, 'https://zoom.us/j/9876543210?pwd=test')
        self.assertEqual(batch.schedule_days, 'Mon, Wed, Fri')
        self.assertEqual(batch.schedule_time, '19:00 - 21:00 IST')
        self.assertEqual(batch.full_schedule, 'Every Mon, Wed, Fri from 19:00 to 21:00 IST')

        # Verify auto-generated sessions for the next 4 weeks
        sessions = BatchSession.objects.filter(batch=batch)
        self.assertGreaterEqual(sessions.count(), 10)  # ~12 sessions across Mon, Wed, Fri
        first_session = sessions.first()
        self.assertEqual(first_session.meeting_link, 'https://zoom.us/j/9876543210?pwd=test')
        self.assertEqual(first_session.status, 'UPCOMING')

    def test_create_batch_mandatory_field_validation(self):
        """
        Verify that missing mandatory fields (Name, GitHub Path, GDrive Path) trigger validation errors.
        """
        self.client.force_login(self.admin_user)

        # Missing github_path and gdrive_path
        resp = self.client.post('/lms/batches/create/', {
            'name': 'Incomplete Cohort',
            'next': '/lms/?tab=batches',
        }, follow=True)

        self.assertFalse(Batch.objects.filter(name='Incomplete Cohort').exists())
        self.assertContains(resp, 'Failed to create batch:')
        self.assertContains(resp, 'github_path')
        self.assertContains(resp, 'gdrive_path')

    def test_batch_ui_renders_schedule_and_resource_links(self):
        """
        Verify batch card in admin dashboard and batch detail page render
        GitHub path, GDrive path, Zoom link, and recurring schedule badge.
        """
        batch = Batch.objects.create(
            name='Autonomous Systems Cohort Beta',
            code='AUTO-BETA',
            github_path='https://github.com/org/auto-beta',
            gdrive_path='https://drive.google.com/drive/folders/auto-beta',
            zoom_link='https://zoom.us/j/1122334455',
            schedule_days='Tue, Thu',
            schedule_time='18:00 - 20:00 IST',
            schedule='Every Tue, Thu at 18:00 - 20:00 IST',
            status='ONGOING'
        )

        self.client.force_login(self.admin_user)

        # 1. Dashboard Batches Tab
        resp_dash = self.client.get('/lms/?tab=batches')
        self.assertEqual(resp_dash.status_code, 200)
        self.assertContains(resp_dash, 'https://github.com/org/auto-beta')
        self.assertContains(resp_dash, 'https://drive.google.com/drive/folders/auto-beta')
        self.assertContains(resp_dash, 'https://zoom.us/j/1122334455')
        self.assertContains(resp_dash, 'Every Tue, Thu at 18:00 - 20:00 IST')

        # 2. Batch Detail Hub
        resp_detail = self.client.get(f'/lms/batches/{batch.id}/')
        self.assertEqual(resp_detail.status_code, 200)
        self.assertContains(resp_detail, 'https://github.com/org/auto-beta')
        self.assertContains(resp_detail, 'https://drive.google.com/drive/folders/auto-beta')
        self.assertContains(resp_detail, 'https://zoom.us/j/1122334455')
        self.assertContains(resp_detail, 'Every Tue, Thu at 18:00 - 20:00 IST')
        self.assertContains(resp_detail, 'Recurring: Tue, Thu')

    def test_batch_creation_without_explicit_status_defaults_to_ongoing(self):
        """
        Ensure batch creation succeeds when status is omitted from POST data,
        defaulting to 'ONGOING' and auto-normalizing URLs.
        """
        self.client.force_login(self.admin_user)
        post_data = {
            'name': 'AI Systems Engineering 2026',
            'github_path': 'github.com/aptcomputinglabs/ai-systems',
            'gdrive_path': 'drive.google.com/drive/folders/ai-systems',
            'zoom_link': 'zoom.us/j/9876543210',
            'schedule_days': 'Mon, Wed, Fri',
            'schedule_time': '19:00 - 21:00 IST',
            'schedule': 'Every Mon, Wed, Fri at 19:00 - 21:00 IST',
            'next': '/lms/?tab=batches',
        }
        resp = self.client.post('/lms/batches/create/', post_data, follow=True)
        self.assertEqual(resp.status_code, 200)

        batch = Batch.objects.filter(name='AI Systems Engineering 2026').first()
        self.assertIsNotNone(batch, "Batch should be created in database")
        self.assertEqual(batch.status, 'ONGOING')
        self.assertEqual(batch.github_path, 'https://github.com/aptcomputinglabs/ai-systems')
        self.assertEqual(batch.gdrive_path, 'https://drive.google.com/drive/folders/ai-systems')
        self.assertEqual(batch.zoom_link, 'https://zoom.us/j/9876543210')
        self.assertContains(resp, 'AI Systems Engineering 2026')

    def test_batch_creation_ajax_endpoint(self):
        """
        Verify AJAX submission returns JSON with batch id, code, and redirect URL.
        """
        self.client.force_login(self.admin_user)
        post_data = {
            'name': 'Full Stack Agentic Batch',
            'github_path': 'https://github.com/aptcomputinglabs/agentic',
            'gdrive_path': 'https://drive.google.com/drive/folders/agentic',
        }
        resp = self.client.post('/lms/batches/create/', post_data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        self.assertIn('batch_id', data)
        self.assertIn('code', data)
        self.assertEqual(data['redirect_url'], '/lms/?tab=batches')

    def test_batch_appears_on_dashboard_landing_page(self):
        """
        Verify newly created batch is displayed on the main /lms/ dashboard landing page.
        """
        batch = Batch.objects.create(
            name='Cloud Native DevOps Cohort 2026',
            code='DEVOPS-2026',
            github_path='https://github.com/aptcomputinglabs/devops',
            gdrive_path='https://drive.google.com/drive/folders/devops',
            zoom_link='https://zoom.us/j/555444333',
            schedule='Every Sat, Sun from 10:00 to 13:00 IST',
            status='ONGOING'
        )
        self.client.force_login(self.admin_user)
        resp = self.client.get('/lms/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Cloud Native DevOps Cohort 2026')
        self.assertContains(resp, 'DEVOPS-2026')
        self.assertContains(resp, 'Every Sat, Sun from 10:00 to 13:00 IST')

    def test_batch_creation_without_zoom_link_succeeds(self):
        """
        Verify that Zoom Meeting Link is completely optional when filling batch details,
        and that sessions are still generated based on schedule.
        """
        self.client.force_login(self.admin_user)
        post_data = {
            'name': 'Python Data Engineering Cohort 2026',
            'github_path': 'https://github.com/aptcomputinglabs/python-data',
            'gdrive_path': 'https://drive.google.com/drive/folders/python-data',
            'zoom_link': '',  # Omitted / blank
            'schedule_days': 'Mon, Wed, Fri',
            'schedule_time': '19:00 - 21:00 IST',
            'schedule': 'Every Mon, Wed, Fri at 19:00 - 21:00 IST',
            'auto_generate_sessions': 'on',
        }
        resp = self.client.post('/lms/batches/create/', post_data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])

        batch = Batch.objects.filter(name='Python Data Engineering Cohort 2026').first()
        self.assertIsNotNone(batch)
        self.assertEqual(batch.zoom_link, '')
        # Verify upcoming sessions were generated for this batch
        self.assertTrue(batch.sessions.count() > 0)

        # Verify page renders cleanly without zoom link
        resp_dash = self.client.get('/lms/?tab=batches')
        self.assertEqual(resp_dash.status_code, 200)
        self.assertContains(resp_dash, 'Python Data Engineering Cohort 2026')





