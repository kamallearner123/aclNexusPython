from decimal import Decimal
from django.db import models
from django.db.models import UniqueConstraint


class LMSBaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True


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

    @property
    def full_name(self):
        name = f"{self.first_name} {self.last_name}".strip()
        return name if name else self.email.split('@')[0]

    def __str__(self):
        return f"{self.email} ({self.role})"


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

    def __str__(self):
        return f"{self.instructor.full_name} - {self.course.code} ({self.role})"


class Module(LMSBaseModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.course.code} - M{self.order}: {self.title}"


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

    def __str__(self):
        return f"{self.module.course.code} - L{self.order}: {self.title}"


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

    def __str__(self):
        return f"User {self.external_user_id} in {self.course.code} ({self.progress_percent}%)"


class LessonProgress(LMSBaseModel):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name='lesson_progress')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='student_progress')
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=['enrollment', 'lesson'], name='unique_enrollment_lesson_progress')
        ]

    def __str__(self):
        return f"Enrollment {self.enrollment_id} - Lesson {self.lesson_id} ({self.completed})"


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

    def __str__(self):
        return f"{self.course.code} Broadcast: {self.title}"


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

    def __str__(self):
        return f"{self.course.code} Live: {self.title} on {self.scheduled_date}"


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

    def __str__(self):
        return f"{self.course.code} - {self.title}"


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

    def __str__(self):
        return f"Submission: {self.assignment.title} by User {self.external_user_id} ({self.status})"


class Certificate(LMSBaseModel):
    certificate_number = models.CharField(max_length=64, unique=True)
    enrollment = models.OneToOneField(Enrollment, on_delete=models.CASCADE, related_name='certificate')
    issued_at = models.DateTimeField(auto_now_add=True)
    pdf_file = models.FileField(upload_to='certificates/', blank=True, null=True)

    def __str__(self):
        return f"Certificate {self.certificate_number} for {self.enrollment.course.code}"


class StudentActivity(LMSBaseModel):
    external_user_id = models.PositiveBigIntegerField(db_index=True)
    activity_type = models.CharField(max_length=50)  # LESSON_COMPLETED, ASSIGNMENT_SUBMITTED, LIVE_CLASS_JOINED, etc.
    title = models.CharField(max_length=255)
    detail = models.CharField(max_length=255, blank=True)
    score = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Activity ({self.activity_type}) for User {self.external_user_id}: {self.title}"


class StudentBadge(LMSBaseModel):
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=255)
    icon = models.CharField(max_length=50, default='award')
    color = models.CharField(max_length=50, default='purple')

    def __str__(self):
        return self.name


class Batch(LMSBaseModel):
    STATUS_CHOICES = [
        ('UPCOMING', 'Upcoming'),
        ('ONGOING', 'Ongoing / Active'),
        ('COMPLETED', 'Completed'),
        ('ARCHIVED', 'Archived'),
    ]

    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True, related_name='batches')
    github_path = models.CharField(max_length=500, blank=True, default='', help_text="GitHub repository URL or path")
    gdrive_path = models.CharField(max_length=500, blank=True, default='', help_text="Google Drive folder URL or path")
    schedule_days = models.CharField(max_length=100, blank=True, default='', help_text="Repetitive schedule days, e.g., Mon, Wed, Fri")
    schedule_time = models.CharField(max_length=100, blank=True, default='', help_text="Schedule time, e.g., 18:00 - 20:00")
    schedule = models.CharField(max_length=255, blank=True, default='', help_text="Repetitive schedule summary")
    zoom_link = models.CharField(max_length=500, blank=True, default='', help_text="Zoom / Google Meet recurring meeting link")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ONGOING')
    students = models.ManyToManyField(LMSUser, related_name='student_batches', blank=True)
    mentors = models.ManyToManyField(LMSUser, related_name='mentor_batches', blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['-start_date', 'code']

    def __str__(self):
        return f"[{self.code}] {self.name}"

    @property
    def full_schedule(self):
        if self.schedule:
            return self.schedule
        if self.schedule_days and self.schedule_time:
            return f"{self.schedule_days} @ {self.schedule_time}"
        return self.schedule_days or self.schedule_time or "Flexible Schedule"

    @property
    def students_count(self):
        return self.students.count()

    @property
    def mentors_count(self):
        return self.mentors.count()

    @property
    def github_url(self):
        val = (self.github_path or '').strip()
        if val and not val.startswith(('http://', 'https://', 'git@')):
            return f"https://{val}"
        return val

    @property
    def gdrive_url(self):
        val = (self.gdrive_path or '').strip()
        if val and not val.startswith(('http://', 'https://')):
            return f"https://{val}"
        return val

    @property
    def zoom_url(self):
        val = (self.zoom_link or '').strip()
        if val and not val.startswith(('http://', 'https://')):
            return f"https://{val}"
        return val


class StudentPayment(LMSBaseModel):
    STATUS_CHOICES = [
        ('PAID', 'Paid / Verified'),
        ('PARTIAL', 'Partially Paid'),
        ('PENDING', 'Pending / Unpaid'),
        ('OVERDUE', 'Overdue'),
        ('WAIVED', 'Waived / Scholarship'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('UPI', 'UPI / QR Code'),
        ('BANK_TRANSFER', 'Bank Transfer / NEFT / IMPS'),
        ('CREDIT_DEBIT_CARD', 'Credit / Debit Card'),
        ('CASH', 'Cash / Direct'),
        ('ONLINE', 'Online Gateway'),
        ('OTHER', 'Other'),
    ]

    student = models.ForeignKey(LMSUser, on_delete=models.CASCADE, related_name='payments')
    batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    title = models.CharField(max_length=255, default='Tuition & Course Fee')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    due_date = models.DateField(null=True, blank=True)
    payment_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHOD_CHOICES, default='UPI')
    transaction_reference = models.CharField(max_length=255, blank=True, help_text="UTR / UPI Txn ID / Reference Number")
    paid_at = models.DateTimeField(null=True, blank=True)
    receipt_number = models.CharField(max_length=64, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student.full_name} - {self.title} ({self.payment_status})"

    @property
    def balance_due(self):
        return max(Decimal('0.00'), self.total_amount - self.amount_paid)

    @property
    def is_fully_paid(self):
        return self.amount_paid >= self.total_amount and self.total_amount > 0


class BatchSession(LMSBaseModel):
    STATUS_CHOICES = [
        ('UPCOMING', 'Upcoming'),
        ('LIVE', 'Live / In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='sessions')
    title = models.CharField(max_length=255)
    instructor = models.ForeignKey(LMSUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='batch_sessions')
    scheduled_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    meeting_link = models.URLField(help_text="Google Meet / Zoom URL")
    recording_link = models.URLField(blank=True, null=True, help_text="Session recording URL if completed")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='UPCOMING')
    agenda = models.TextField(blank=True, help_text="Topics and lab objectives for this session")

    class Meta:
        ordering = ['scheduled_date', 'start_time']

    def __str__(self):
        return f"[{self.batch.code}] {self.title} on {self.scheduled_date}"


class BatchMaterial(LMSBaseModel):
    MATERIAL_TYPE_CHOICES = [
        ('SLIDES', 'Slide Deck / Presentation'),
        ('CODE_REPO', 'Source Code / GitHub Repo'),
        ('DOCUMENT', 'Lecture Notes / Document'),
        ('RECORDING', 'Class Video Recording'),
        ('ASSIGNMENT', 'Lab Assignment / Exercise'),
        ('ATTACHMENT', 'File Attachment / Download'),
        ('OTHER', 'Other Resource'),
    ]

    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='materials')
    session = models.ForeignKey(BatchSession, on_delete=models.SET_NULL, null=True, blank=True, related_name='materials')
    title = models.CharField(max_length=255)
    material_type = models.CharField(max_length=30, choices=MATERIAL_TYPE_CHOICES, default='DOCUMENT')
    external_url = models.URLField(blank=True, null=True, help_text="Drive, GitHub, or Colab link")
    attachment_file = models.FileField(upload_to='batch_materials/', blank=True, null=True)
    description = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(LMSUser, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.batch.code}] {self.title} ({self.material_type})"


class CourseFeedback(LMSBaseModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='feedbacks')
    user = models.ForeignKey(LMSUser, on_delete=models.CASCADE, related_name='course_feedbacks')
    batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, null=True, blank=True, related_name='course_feedbacks')
    rating = models.PositiveSmallIntegerField(default=5)  # 1-5 stars
    title = models.CharField(max_length=255, blank=True, default='')
    comment = models.TextField()
    is_public = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.full_name} ({self.rating}★) on {self.course.code}"


class BatchAssignment(LMSBaseModel):
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('ARCHIVED', 'Archived'),
    ]
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='assignments')
    title = models.CharField(max_length=255)
    description = models.TextField()
    due_date = models.DateTimeField(null=True, blank=True)
    max_score = models.PositiveIntegerField(default=100)
    resource_url = models.URLField(blank=True, null=True, help_text="Starter code or GitHub repo")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    assigned_by = models.ForeignKey(LMSUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_assignments')
    # If target_student is None, it is sent to ALL students in the batch!
    target_student = models.ForeignKey(LMSUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_batch_tasks')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        target = self.target_student.full_name if self.target_student else "All Students"
        return f"{self.batch.code} - {self.title} ({target})"


class SessionAttendance(LMSBaseModel):
    STATUS_CHOICES = [
        ('PRESENT', 'Present'),
        ('ABSENT', 'Absent'),
        ('LATE', 'Late'),
        ('EXCUSED', 'Excused'),
    ]
    session = models.ForeignKey(BatchSession, on_delete=models.CASCADE, related_name='attendances')
    student = models.ForeignKey(LMSUser, on_delete=models.CASCADE, related_name='session_attendances')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PRESENT')
    marked_by = models.ForeignKey(LMSUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='marked_attendances')
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=['session', 'student'], name='unique_session_student_attendance')
        ]

    def __str__(self):
        return f"{self.session.title} - {self.student.full_name}: {self.status}"


class BatchAssignmentAssessment(LMSBaseModel):
    STATUS_CHOICES = [
        ('PENDING', 'Pending / Not Graded'),
        ('GRADED', 'Graded / Assessed'),
        ('REVISION_REQUESTED', 'Revision Requested'),
        ('EXCUSED', 'Excused'),
    ]
    assignment = models.ForeignKey(BatchAssignment, on_delete=models.CASCADE, related_name='assessments')
    student = models.ForeignKey(LMSUser, on_delete=models.CASCADE, related_name='batch_assignment_assessments')
    score = models.PositiveIntegerField(null=True, blank=True)
    max_score = models.PositiveIntegerField(default=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='GRADED')
    mentor_feedback = models.TextField(blank=True)
    assessed_by = models.ForeignKey(LMSUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='graded_batch_assessments')
    submission_url = models.URLField(blank=True, null=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=['assignment', 'student'], name='unique_batch_assignment_student_assessment')
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.assignment.title} - {self.student.full_name}: {self.score}/{self.max_score} ({self.status})"


class MentorMessage(LMSBaseModel):
    student = models.ForeignKey(LMSUser, on_delete=models.CASCADE, related_name='sent_mentor_messages')
    mentor = models.ForeignKey(LMSUser, on_delete=models.CASCADE, related_name='received_student_messages')
    sender = models.ForeignKey(LMSUser, on_delete=models.CASCADE, related_name='authored_mentor_messages')
    batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, null=True, blank=True, related_name='mentor_messages')
    message = models.TextField()
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {self.sender.full_name}: {self.message[:30]}"

