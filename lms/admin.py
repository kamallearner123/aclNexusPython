from django.contrib import admin
from .models import (
    LMSUser,
    Course,
    CourseInstructor,
    Module,
    Lesson,
    Enrollment,
    LessonProgress,
    CourseCommandMessage,
    LiveClass,
    Assignment,
    AssignmentSubmission,
    Certificate,
    StudentActivity,
    StudentBadge,
)


@admin.register(LMSUser)
class LMSUserAdmin(admin.ModelAdmin):
    list_display = ['email', 'external_user_id', 'role', 'first_name', 'last_name', 'is_active']
    search_fields = ['email', 'first_name', 'last_name']
    list_filter = ['role', 'is_active']


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['code', 'title', 'status', 'enrolled_count', 'is_active']
    search_fields = ['code', 'title']
    list_filter = ['status', 'is_active']
    prepopulated_fields = {'slug': ('title',)}


@admin.register(CourseInstructor)
class CourseInstructorAdmin(admin.ModelAdmin):
    list_display = ['course', 'instructor', 'role', 'is_primary']
    list_filter = ['role', 'is_primary']


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'order']
    list_filter = ['course']


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ['title', 'module', 'lesson_type', 'duration_minutes', 'order', 'is_required']
    list_filter = ['module__course', 'lesson_type', 'is_required']


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['external_user_id', 'course', 'status', 'progress_percent', 'enrolled_at']
    list_filter = ['status', 'course']


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ['enrollment', 'lesson', 'completed', 'completed_at']
    list_filter = ['completed']


@admin.register(CourseCommandMessage)
class CourseCommandMessageAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'next_class_topic', 'next_class_datetime', 'is_active']
    list_filter = ['course', 'is_active']


@admin.register(LiveClass)
class LiveClassAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'instructor', 'scheduled_date', 'start_time', 'status']
    list_filter = ['course', 'status', 'scheduled_date']


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'due_date', 'max_score', 'status']
    list_filter = ['course', 'status']


@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(admin.ModelAdmin):
    list_display = ['assignment', 'external_user_id', 'status', 'grade_score', 'submitted_at']
    list_filter = ['status', 'assignment__course']


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ['certificate_number', 'enrollment', 'issued_at']


@admin.register(StudentActivity)
class StudentActivityAdmin(admin.ModelAdmin):
    list_display = ['external_user_id', 'activity_type', 'title', 'created_at']
    list_filter = ['activity_type']


@admin.register(StudentBadge)
class StudentBadgeAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon', 'color']
