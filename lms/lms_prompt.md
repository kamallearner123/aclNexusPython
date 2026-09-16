# LEARNHUB LMS — MASTER SYSTEM BUILD SPECIFICATION
**Document Version**: 2.0 (Production-Grade Architecture & Implementation Contract)  
**Target Environment**: Python 3.12+ / Django 5.x / Multi-Database SQLite & PostgreSQL  
**Primary Objective**: Build a complete, enterprise-grade Learning Management System with strict database isolation, server-side RBAC, dynamic live sessions, assignment verification loops, course command broadcasts, and zero mock/dummy data.

---

```markdown
# 01. Product Definition & Vision

**LearnHub LMS** is an enterprise-grade learning and curriculum delivery platform engineered for engineering cohorts, technical professionals, and corporate upskilling. 

The platform supports:
1. Structured modular curriculum delivery (chapters, lessons, articles, labs, code repositories).
2. Course Command Broadcasts: Real-time dispatches from instructors featuring previous class takeaways, video recordings, and next session agendas.
3. Interactive Live Sessions: Real-time display of the next two upcoming classes with direct video conferencing meeting links.
4. Milestone & Task Deliverable Verification: Hands-on student assignment submissions (code repositories, pull requests, notebooks) with mentor grading and revision loops.
5. Faculty Mentoring & Doubt Desks: Multi-instructor support per course with 1-on-1 access.
6. Real, Persisted Student Analytics: Live lesson progress, completion metrics, and verifiable certificates derived strictly from database records.

---

## 02. System Architecture & Boundaries

### Technology Stack
- **Backend Framework**: Python 3.12+, Django 5.x
- **Architecture**: Domain-Driven, Service-Layered Architecture with strict separation of concerns (Models, Services/Selectors, Forms, Views, Templates).
- **Databases**:
  - Primary / Default (`db.sqlite3` in dev, PostgreSQL in prod): ERP core identity, organization, permissions.
  - LMS Database (`lms_db.sqlite3` in dev, PostgreSQL in prod): LMS-exclusive tables.
- **Frontend / Rendering**: Django Templates, Semantic HTML5, Vanilla CSS / Tailwind CSS, Lucide Icons, Vanilla JavaScript.
- **Timezone**: `Asia/Kolkata` (IST) with `USE_TZ = True`.

### Directory Organization
```text
project/
├── core/                       # Primary ERP / Identity system
│   ├── models.py               # User, Role, UserRole
│   └── views.py                # Core authentication and portal entry
├── lms/                        # Isolated LMS Domain
│   ├── models.py               # LMSUser, Course, Module, Lesson, etc.
│   ├── router.py               # LMSDatabaseRouter
│   ├── forms.py                # Validated Django forms
│   ├── services.py             # Progress calculation, enrollment, grading services
│   ├── selectors.py            # Optimized query services & dashboard aggregators
│   ├── views.py                # Protected HTTP endpoints
│   ├── urls.py                 # Named LMS route configurations
│   └── management/commands/    # Idempotent seed commands (seed_lms.py)
├── templates/
│   └── lms/                    # Modular Django templates
└── static/img/lms/             # Production vector banners and assets
```

---

## 03. Authentication & Identity Ownership

### 3.1 Identity Boundary
- **Authentication Ownership**: The primary ERP system (`core.User`) owns user authentication, credential hashing, login sessions, and password management.
- **LMS Profile Ownership**: `lms.LMSUser` owns learning-specific attributes: cohort role, specialization, biography, phone, avatar, and academic status.
- **Cross-Database Identity Link**:
  - `LMSUser` references the ERP identity exclusively via an immutable integer field: `external_user_id`.
  - **Critical Rule**: Cross-database relationships must **never** use Django `models.ForeignKey` constraints across separate physical databases.
  - The application service layer is strictly responsible for validating existence and synchronizing user identity upon authentication.
- **Zero Plaintext Passwords / Zero Password Hints**:
  - Passwords are never stored or duplicated in LMS tables.
  - Any field resembling `password_hint` is strictly prohibited.
  - All password validation utilizes Django's PBKDF2/Argon2 password hashers in the primary database.

---

## 04. Multi-Database Isolation

### 4.1 Database Configuration (`settings.py`)
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    },
    'lms': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'lms_db.sqlite3',
    }
}
DATABASE_ROUTERS = ['lms.router.LMSDatabaseRouter']
```

### 4.2 Multi-Database Router (`lms/router.py`)
The router guarantees zero leakage between ERP and LMS databases:
```python
class LMSDatabaseRouter:
    route_app_labels = {'lms'}

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.route_app_labels:
            return 'lms'
        return 'default'

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.route_app_labels:
            return 'lms'
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        # Allow relations only if both models reside in the same database app
        if (obj1._meta.app_label in self.route_app_labels and obj2._meta.app_label in self.route_app_labels) or \
           (obj1._meta.app_label not in self.route_app_labels and obj2._meta.app_label not in self.route_app_labels):
            return True
        return False

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label in self.route_app_labels:
            return db == 'lms'
        return db == 'default'
```

---

## 05. Role-Based Access Control (RBAC) & Authorization

Access control must be enforced on the server in every view and service. Do not rely solely on hiding UI navigation links.

### 5.1 Roles
- `ADMIN`: System administrator; full system, cohort, and course authority.
- `MANAGER`: Academic manager / lead; curriculum design, scheduling, enrollment.
- `MENTOR`: Faculty instructor; broadcast dispatch, assignment creation, grading, live classes.
- `STUDENT`: Active enrolled learner; course participation, deliverable submissions.
- `USER`: General portal member without course enrollment.

### 5.2 Server-Side Permission Matrix
| Capability | ADMIN | MANAGER | MENTOR | STUDENT | USER |
|:---|:---:|:---:|:---:|:---:|:---:|
| View LMS Dashboard & Enrolled Courses | Yes | Yes | Yes | Yes | Yes |
| Edit Own Profile | Yes | Yes | Yes | Yes | Yes |
| Create / Manage Users & Cohorts | Yes | Yes | No | No | No |
| Create & Publish Courses / Modules | Yes | Yes | No | No | No |
| Publish Course Command Message | Yes | Yes | Yes | No | No |
| Create & Edit Assignments | Yes | Yes | Yes | No | No |
| Grade & Review Deliverables | Yes | Yes | Yes | No | No |
| Schedule Live Classes | Yes | Yes | Yes | No | No |
| Issue / Revoke Certificates | Yes | Yes | No | No | No |
| Submit Deliverable Solutions | No | No | No | Yes | No |

---

## 06. Complete Database Models (`lms/models.py`)

All LMS models inherit from `LMSBaseModel` (`id`, `created_at`, `updated_at`, `is_active`):

```python
from django.db import models
from django.db.models import UniqueConstraint

class LMSBaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True
```

### 6.1 `LMSUser`
```python
class LMSUser(LMSBaseModel):
    ROLE_CHOICES = [
        ('ADMIN', 'System Admin'),
        ('MANAGER', 'Manager / Academic Lead'),
        ('MENTOR', 'Faculty Mentor / Instructor'),
        ('STUDENT', 'Student / Learner'),
        ('USER', 'Portal User'),
    ]

    external_user_id = models.PositiveBigIntegerField(unique=True, db_index=True)
    email = models.EmailField(unique=True, max_length=255)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='STUDENT')
    specialization = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    bio = models.TextField(blank=True)
    avatar_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return f"{self.email} ({self.role})"
```

### 6.2 `Course` & `CourseInstructor`
```python
class Course(LMSBaseModel):
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PUBLISHED', 'Published'),
        ('ARCHIVED', 'Archived'),
    ]

    code = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    short_description = models.CharField(max_length=500)
    description = models.TextField()
    category = models.CharField(max_length=100, default='Artificial Intelligence')
    difficulty_level = models.CharField(max_length=50, default='Intermediate')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PUBLISHED')
    thumbnail = models.CharField(max_length=255, blank=True, default='genai.svg')
    enrolled_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"[{self.code}] {self.title}"

class CourseInstructor(LMSBaseModel):
    ROLE_CHOICES = [
        ('LEAD', 'Lead Instructor'),
        ('ASSISTANT', 'Assistant Mentor'),
        ('ADVISOR', 'Technical Advisor'),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='instructors')
    instructor = models.ForeignKey(LMSUser, on_delete=models.CASCADE, related_name='teaching_courses')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='LEAD')
    is_primary = models.BooleanField(default=False)

    class Meta:
        constraints = [
            UniqueConstraint(fields=['course', 'instructor'], name='unique_course_instructor')
        ]
```

### 6.3 `Module` & `Lesson`
```python
class Module(LMSBaseModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['order', 'id']

class Lesson(LMSBaseModel):
    TYPE_CHOICES = [
        ('VIDEO', 'Video Lecture'),
        ('ARTICLE', 'Article / Guide'),
        ('QUIZ', 'Interactive Quiz'),
        ('LAB', 'Hands-on Lab'),
        ('PDF', 'PDF Resource'),
    ]

    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=255)
    lesson_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='ARTICLE')
    duration_minutes = models.PositiveIntegerField(default=15)
    video_url = models.URLField(blank=True, null=True)
    content = models.TextField(blank=True)
    resource_link = models.URLField(blank=True, null=True)
    order = models.PositiveIntegerField(default=1)
    is_required = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'id']
```

### 6.4 `Enrollment` & `LessonProgress`
```python
class Enrollment(LMSBaseModel):
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('PAUSED', 'Paused'),
    ]

    external_user_id = models.PositiveBigIntegerField(db_index=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    enrolled_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    progress_percent = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            UniqueConstraint(fields=['external_user_id', 'course'], name='unique_user_course_enrollment')
        ]

class LessonProgress(LMSBaseModel):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name='lesson_progress')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='student_progress')
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=['enrollment', 'lesson'], name='unique_enrollment_lesson_progress')
        ]
```

### 6.5 `CourseCommandMessage`
```python
class CourseCommandMessage(LMSBaseModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='command_messages')
    title = models.CharField(max_length=255)
    previous_session_summary = models.TextField(help_text="Key takeaways and architectural recap of previous class")
    previous_session_recording_url = models.URLField(blank=True, null=True)
    next_class_topic = models.CharField(max_length=255, help_text="Detailed agenda for upcoming session")
    next_class_datetime = models.DateTimeField()
    next_class_link = models.URLField(help_text="Direct Zoom / Google Meet meeting URL")
    published_by_id = models.PositiveBigIntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']
```

### 6.6 `LiveClass`
```python
class LiveClass(LMSBaseModel):
    STATUS_CHOICES = [
        ('UPCOMING', 'Upcoming'),
        ('LIVE', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    title = models.CharField(max_length=255)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='live_classes')
    instructor = models.ForeignKey(LMSUser, on_delete=models.CASCADE, related_name='live_sessions')
    scheduled_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    meeting_url = models.URLField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='UPCOMING')

    class Meta:
        ordering = ['scheduled_date', 'start_time']
```

### 6.7 `Assignment` & `AssignmentSubmission`
```python
class Assignment(LMSBaseModel):
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('ARCHIVED', 'Archived'),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='assignments')
    title = models.CharField(max_length=255)
    description = models.TextField()
    due_date = models.DateTimeField(null=True, blank=True)
    max_score = models.PositiveIntegerField(default=100)
    resource_url = models.URLField(blank=True, null=True, help_text="Starter code or GitHub repo")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['order', 'due_date']

class AssignmentSubmission(LMSBaseModel):
    STATUS_CHOICES = [
        ('SUBMITTED', 'Submitted for Review'),
        ('REVIEWED', 'Reviewed / Graded'),
        ('REVISION_REQUESTED', 'Revision Requested'),
    ]

    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    external_user_id = models.PositiveBigIntegerField(db_index=True)
    submission_url = models.URLField(help_text="GitHub PR / Repo / Colab notebook URL")
    submission_text = models.TextField(blank=True, help_text="Solution notes and architecture decisions")
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SUBMITTED')
    grade_score = models.PositiveIntegerField(null=True, blank=True)
    mentor_feedback = models.TextField(blank=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=['assignment', 'external_user_id'], name='unique_assignment_student_submission')
        ]
```

### 6.8 `Certificate`, `StudentActivity`, & `StudentBadge`
```python
class Certificate(LMSBaseModel):
    certificate_number = models.CharField(max_length=64, unique=True)
    enrollment = models.OneToOneField(Enrollment, on_delete=models.CASCADE, related_name='certificate')
    issued_at = models.DateTimeField(auto_now_add=True)
    pdf_file = models.FileField(upload_to='certificates/', blank=True, null=True)

class StudentActivity(LMSBaseModel):
    external_user_id = models.PositiveBigIntegerField(db_index=True)
    activity_type = models.CharField(max_length=50) # LESSON_COMPLETED, ASSIGNMENT_SUBMITTED, LIVE_CLASS_JOINED
    title = models.CharField(max_length=255)
    detail = models.CharField(max_length=255, blank=True)
    score = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

class StudentBadge(LMSBaseModel):
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=255)
    icon = models.CharField(max_length=50, default='award')
    color = models.CharField(max_length=50, default='purple')
```

---

## 07. Progress Engine & Mathematical Specifications

Never hardcode or estimate progress values. Compute exact progress using the following mathematical formulas:

### 7.1 Course Progress Formula
$$\text{Course Progress (\%)} = \text{round}\left( \frac{\text{Completed Required Lessons in Course}}{\text{Total Required Lessons in Course}} \times 100 \right)$$

### 7.2 Overall Learner Progress Formula
$$\text{Overall Progress (\%)} = \text{round}\left( \frac{\sum_{\text{Enrolled Courses}} \text{Completed Required Lessons}}{\sum_{\text{Enrolled Courses}} \text{Total Required Lessons}} \times 100 \right)$$

### 7.3 Progress Update Workflow
Whenever a student marks a lesson completed:
1. `LessonProgress` record is upserted with `completed = True` and `completed_at = timezone.now()`.
2. `Enrollment.progress_percent` is recalculated using Formula 7.1.
3. If `progress_percent == 100`, `Enrollment.status` is updated to `'COMPLETED'`, issuing a `Certificate` record if none exists.
4. A `StudentActivity` entry is created: `activity_type = 'LESSON_COMPLETED'`.

---

## 08. Live Classes & "Next Two Sessions" Query Engine

### 8.1 Presentation Requirements
- Display strictly in **Asia/Kolkata (IST)** timezone.
- For each enrolled course, query and display exactly the **next two upcoming sessions**:
  ```python
  next_two_sessions = list(LiveClass.objects.filter(
      course=course,
      is_active=True,
      status__in=['UPCOMING', 'LIVE'],
      scheduled_date__gte=timezone.now().date()
  ).order_by('scheduled_date', 'start_time')[:2])
  ```
- **Session Card Elements**:
  1. Date badge (Day, Month).
  2. Session number pill (`Session #1`, `Session #2`).
  3. Start and end time in 12-hour IST format (e.g. `7:00 PM - 8:30 PM IST`).
  4. Instructor name and avatar.
  5. Direct green CTA button: **"Join Live Session Now &rarr;"** opening `meeting_url` in a new tab (`target="_blank" rel="noopener noreferrer"`).
- Feature the active `CourseCommandMessage` recap card immediately above the session cards.

---

## 09. Assignment Deliverables & Verification Workflow

### 9.1 Submission State Machine
```text
[PENDING] 
   │
   ▼ Student submits GitHub/PR URL & notes
[SUBMITTED FOR REVIEW]
   │
   ├─► Mentor reviews & approves (Grade ≥ 70%) ──► [REVIEWED / GRADED]
   │
   └─► Mentor requests changes ──────────────────► [REVISION_REQUESTED]
```

### 9.2 Submission Rules
- Enforce the `UniqueConstraint` on `['assignment', 'external_user_id']`.
- Submitting an assignment when a record exists must **update** the deliverable URL, notes, and reset status to `'SUBMITTED'`.
- Grade score validation: `0 <= grade_score <= assignment.max_score`.
- Submission modal requires:
  - Deliverable URL (`url`, required).
  - Implementation notes / architectural summary (`textarea`, optional).

---

## 10. Faculty Mentoring System

- Mentors must never be hardcoded into templates.
- Mentors are resolved directly from `CourseInstructor` relations linked to active `LMSUser` records.
- Display mentor profile cards containing:
  - Full Name, Designation, and Specialization.
  - Biography and area of expertise.
  - Courses they mentor.
  - Direct contact action (`mailto:` or integrated technical doubt desk).

---

## 11. Profile View & Edit (`/lms/profile/`)

- Built referencing enterprise profile editors.
- **Editable Fields**:
  - First Name, Last Name, Phone Number, Specialization, Biography.
- **Read-Only System Fields**:
  - Registered Email Address, Assigned LMS Role.
- **Credential Updates**:
  - Optional password reset form validating old password and updating credentials via Django's auth system in the default database.
- Profile changes persist directly into `LMSUser` in `lms_db.sqlite3`.

---

## 12. Admin Hub & Operational Controls (`/lms/admin-hub/`)

Restricted via server-side permission decorators to `ADMIN` and `MANAGER` roles.

### Operational Modules:
1. **Command Message Broadcast Creator**:
   - Course selector, announcement title, previous session takeaways, video recording link, next class topic, date/time, meeting URL.
   - Deactivates previous command messages for that course and sets new message `is_active = True`.
2. **User & Cohort Management**:
   - Add new students or mentors directly into `lms_db.sqlite3` with matched `external_user_id`.
3. **Assignment Studio**:
   - Create deliverables, point values, due dates, and starter code links.
4. **Live Class Scheduler**:
   - Schedule sessions, assign instructors, specify start/end times and meeting URLs.

---

## 13. UI/UX, Design Language & Client Interactivity

### 13.1 Visual Design Tokens
- **Sidebar Background**: Dark Navy (`#0d1829`), Border (`#1e293b`).
- **Main Viewport Background**: Slate White (`#f8fafc`).
- **Accent Colors**: Blue (`#2563eb`), Emerald (`#10b981`), Purple (`#9333ea`), Amber (`#f59e0b`).
- **Typography**: Inter / System Sans-serif, strict visual hierarchy.
- **Icons**: Lucide SVG icons.

### 13.2 Collapsible Vertical Sidebar
- Toggle button with `panel-left` in top bar and `panel-left-close` in sidebar header.
- Animate smoothly (`transition-all duration-300 ease-in-out`).
- When collapsed (`-ml-64`), the main learning viewport expands to **100% full width**.
- Persist state in `localStorage` key: `lms_sidebar_hidden`:
```javascript
function toggleSidebar() {
    const sidebar = document.getElementById('main-sidebar');
    if (!sidebar) return;
    sidebar.classList.toggle('-ml-64');
    const isHidden = sidebar.classList.contains('-ml-64');
    localStorage.setItem('lms_sidebar_hidden', isHidden ? 'true' : 'false');
}

document.addEventListener('DOMContentLoaded', () => {
    if (localStorage.getItem('lms_sidebar_hidden') === 'true') {
        document.getElementById('main-sidebar')?.classList.add('-ml-64');
    }
});
```

### 13.3 Clean Landing & Unauthenticated Routing
- Root landing page (`/`) must not force login dialogs upfront.
- Accessing protected LMS endpoints redirects to standard login with `?next=/lms/`.
- Logging out (`/logout/`) terminates the user session, flushes session cookies, and redirects cleanly to `/`.

---

## 14. Idempotent Seed Data Command (`seed_lms`)

Create a Django management command: `python manage.py seed_lms`.

### Seed Command Requirements:
1. **Idempotence**: Running multiple times must update existing records and never create duplicates.
2. **Dynamic Dates**: All dates must be computed relative to `timezone.now()` in `Asia/Kolkata` (never hardcode fixed past years).
3. **Environment-Based Credentials**:
   - Read development password from `os.environ.get('SEED_DEFAULT_PASSWORD', 'AclAgentic@123')`.
   - Never commit plaintext production credentials.

### Cohort Specification (17 Users):
| External ID | Email | Role | LMS Role |
|:---:|:---|:---|:---:|
| 2 | `kamal@aptcomputinglabs.com` | Manager / Lead | `MANAGER` |
| 3 | `admin@admin.com` | System Admin | `ADMIN` |
| 4 | `kamalbec2004@gmail.com` | User | `USER` |
| 5 | `roopa@aptcomputinglabs.com` | Team Member | `USER` |
| 6 | `robin@aptcomputinglabs.com` | Team Member | `USER` |
| 7 | `thanseef@aptcomputinglabs.com` | Team Member | `USER` |
| 8 | `supriya@aptcomputinglabs.com` | Lead Instructor | `MENTOR` |
| 9 | `dhanush@aptcomputinglabs.com` | Team Member | `USER` |
| 10 | `supriyathoppana@gmail.com` | User | `USER` |
| 11 | `mageshbj83@gmail.com` | Team Member | `USER` |
| 12 | `emamul.embedded@gmail.com` | Student | `STUDENT` |
| 13 | `sadatul_islama@yahoo.co.in` | Student | `STUDENT` |
| 14 | `balugollapothu67@gmail.com` | Student | `STUDENT` |
| 15 | `srk.kolluru@gmail.com` | Student | `STUDENT` |
| 16 | `hemasundar740@gmail.com` | Student | `STUDENT` |
| 17 | `mdqayyum.se@gmail.com` | Student | `STUDENT` |
| 18 | `lok4979@gmail.com` | Student | `STUDENT` |

### Course 9 Seed Content: "Agentic AI with Examples"
- **Code**: `AGENTIC-AI-2026`
- **Instructor**: `Supriya Thoppana` (Lead Instructor via `CourseInstructor`)
- **Enrollment**: Enroll all 17 users.
- **Command Broadcast**:
  - Title: "Session 4 Recap & Live Architecture Lab Link"
  - Summary: "Deep dive into Autonomous Tool Calling, ReAct loops, and JSON schema validation. Sample notebooks updated under Chapter 3."
  - Recording: `https://www.youtube.com/watch?v=dQw4w9WgXcQ`
  - Next Class: "Building Multi-Agent Workflows & State Graph Routing with LangGraph & Antigravity SDK"
  - Datetime: `timezone.now() + timedelta(days=1, hours=8)`
  - Meeting URL: `https://meet.google.com/acl-agen-tic`
- **Next Two Live Sessions**:
  1. `timezone.now() + timedelta(days=1)`: "Live Lab: Multi-Agent Orchestration & State Graphs" (7:00 PM - 8:30 PM IST)
  2. `timezone.now() + timedelta(days=3)`: "Masterclass: Human-in-the-Loop & Memory Persistence" (7:00 PM - 8:30 PM IST)
- **Assignments**:
  1. "Milestone 1: Build a Tool-Calling Financial & Weather Agent" (Due in 6 days, Max 100 pts)
  2. "Milestone 2: Multi-Agent Supervisor Pattern Implementation" (Due in 12 days, Max 100 pts)

---

## 15. Automated Verification & Quality Assurance Suite

All implementations must pass the automated test suite covering:

```python
# test_lms_architecture.py
class LMSArchitectureTests(TestCase):
    def test_database_isolation(self):
        """Verify LMS tables exist strictly in lms_db.sqlite3 and not default."""
        pass

    def test_cross_database_identity(self):
        """Verify LMSUser references core user via external_user_id without cross-db FK."""
        pass

    def test_assignment_submission_uniqueness(self):
        """Verify student cannot create duplicate submission records for the same assignment."""
        pass

    def test_progress_calculation(self):
        """Verify course progress exactly matches required lesson completion ratio."""
        pass

    def test_live_class_next_two_query(self):
        """Verify only upcoming sessions are queried, ordered by date and capped at 2."""
        pass

    def test_server_side_rbac_enforcement(self):
        """Verify non-admin/non-mentor accounts receive 403 Forbidden on admin-hub."""
        pass
```

---

## 16. Acceptance Criteria

The system build is accepted only when:
1. Both `db.sqlite3` and `lms_db.sqlite3` are configured and routed cleanly.
2. Running `python manage.py migrate --database=lms` executes zero default migrations, and default migrations execute zero LMS migrations.
3. Running `python manage.py seed_lms` is idempotent and seeds all 17 users, Course 9, lessons, command broadcast, live classes, and assignments.
4. Student dashboard displays real mathematical progress (0% initially, dynamically incrementing with lessons).
5. Live classes view renders the next two sessions with functional meeting URLs opening in new tabs.
6. Assignment submission modal accepts URLs and notes, updating the single persisted record.
7. Admin hub allows posting new command messages, instantly updating the broadcast card.
8. Sidebar collapse persists in `localStorage` across page reloads and resizes to 100% full width.
9. All automated unit and integration tests pass with zero errors.
```
