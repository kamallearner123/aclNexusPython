from django import forms
from django.contrib.auth import password_validation
from .models import (
    LMSUser,
    Course,
    CourseCommandMessage,
    LiveClass,
    Assignment,
    AssignmentSubmission,
    Batch,
    BatchSession,
    BatchMaterial,
    StudentPayment,
    BatchAssignment,
    SessionAttendance,
)


class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = LMSUser
        fields = ['first_name', 'last_name', 'phone', 'specialization', 'bio']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'specialization': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'bio': forms.Textarea(attrs={
                'rows': 4,
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm'
            }),
        }


class PasswordUpdateForm(forms.Form):
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm',
            'placeholder': 'Current Password'
        }),
        required=True,
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm',
            'placeholder': 'New Password'
        }),
        required=True,
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm',
            'placeholder': 'Confirm New Password'
        }),
        required=True,
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_old_password(self):
        old_password = self.cleaned_data.get('old_password')
        if not self.user.check_password(old_password):
            raise forms.ValidationError("Current password is not correct.")
        return old_password

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')

        if new_password and confirm_password:
            if new_password != confirm_password:
                self.add_error('confirm_password', "The two password fields didn't match.")
            else:
                password_validation.validate_password(new_password, self.user)
        return cleaned_data


class AssignmentSubmissionForm(forms.ModelForm):
    class Meta:
        model = AssignmentSubmission
        fields = ['submission_url', 'submission_text']
        widgets = {
            'submission_url': forms.URLInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm',
                'placeholder': 'https://github.com/user/repository or Colab link'
            }),
            'submission_text': forms.Textarea(attrs={
                'rows': 4,
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm',
                'placeholder': 'Explain your architectural approach, key decisions, and testing...'
            }),
        }


class AssignmentGradeForm(forms.Form):
    grade_score = forms.IntegerField(
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm',
            'placeholder': 'e.g. 85'
        })
    )
    mentor_feedback = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 4,
            'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm',
            'placeholder': 'Constructive feedback, code quality comments, and recommendations...'
        })
    )


class CourseCommandMessageForm(forms.ModelForm):
    class Meta:
        model = CourseCommandMessage
        fields = [
            'course', 'title', 'previous_session_summary',
            'previous_session_recording_url', 'next_class_topic',
            'next_class_datetime', 'next_class_link'
        ]
        widgets = {
            'course': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm',
                'placeholder': 'e.g. Session 4 Recap & Live Architecture Lab Link'
            }),
            'previous_session_summary': forms.Textarea(attrs={
                'rows': 3,
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm',
                'placeholder': 'Key takeaways and architectural recap...'
            }),
            'previous_session_recording_url': forms.URLInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm',
                'placeholder': 'https://youtube.com/watch?v=...'
            }),
            'next_class_topic': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm',
                'placeholder': 'e.g. Building Multi-Agent Workflows & State Graph Routing'
            }),
            'next_class_datetime': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'next_class_link': forms.URLInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm',
                'placeholder': 'https://meet.google.com/...'
            }),
        }


class LiveClassForm(forms.ModelForm):
    class Meta:
        model = LiveClass
        fields = ['course', 'instructor', 'title', 'scheduled_date', 'start_time', 'end_time', 'meeting_url', 'status']
        widgets = {
            'course': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'instructor': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm',
                'placeholder': 'e.g. Masterclass: Multi-Agent Orchestration'
            }),
            'scheduled_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'start_time': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'end_time': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'meeting_url': forms.URLInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm',
                'placeholder': 'https://meet.google.com/...'
            }),
            'status': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm'
            }),
        }


class AssignmentCreateForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ['course', 'title', 'description', 'due_date', 'max_score', 'resource_url', 'status', 'order']
        widgets = {
            'course': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm',
                'placeholder': 'e.g. Milestone 1: Tool-Calling Agent'
            }),
            'description': forms.Textarea(attrs={
                'rows': 4,
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm',
                'placeholder': 'Deliverable specification, evaluation criteria, and instructions...'
            }),
            'due_date': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'max_score': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'resource_url': forms.URLInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm',
                'placeholder': 'https://github.com/example/starter-repo'
            }),
            'status': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm'
            }),
        }


class CohortUserForm(forms.ModelForm):
    class Meta:
        model = LMSUser
        fields = ['external_user_id', 'email', 'first_name', 'last_name', 'role', 'specialization', 'phone', 'bio']
        widgets = {
            'external_user_id': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm',
                'placeholder': 'Matching Core User ID'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'role': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'specialization': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'bio': forms.Textarea(attrs={
                'rows': 3,
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm'
            }),
        }


class CourseCreateForm(forms.ModelForm):
    lead_instructor = forms.ModelChoiceField(
        queryset=LMSUser.objects.filter(role__in=['MENTOR', 'MANAGER', 'ADMIN'], is_active=True),
        required=False,
        empty_label="-- Select Lead Faculty Mentor / Teacher --",
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none text-sm'
        })
    )
    slug = forms.SlugField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none text-sm',
            'placeholder': 'e.g. multi-agent-systems (optional, auto-generated)'
        })
    )
    thumbnail = forms.CharField(
        required=False,
        initial='genai.svg',
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none text-sm',
            'placeholder': 'genai.svg'
        })
    )
    enroll_all_students = forms.BooleanField(
        required=False,
        initial=True,
        label="Automatically join/enroll all active cohort students into this course immediately"
    )

    class Meta:
        model = Course
        fields = ['code', 'title', 'slug', 'category', 'difficulty_level', 'status', 'short_description', 'description', 'thumbnail']
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none text-sm',
                'placeholder': 'e.g. AI-2026, CLOUD-101'
            }),
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none text-sm',
                'placeholder': 'e.g. Multi-Agent Systems & Generative Workflows'
            }),
            'slug': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none text-sm',
                'placeholder': 'e.g. multi-agent-systems (optional, auto-generated)'
            }),
            'category': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none text-sm',
                'placeholder': 'e.g. Artificial Intelligence, Cloud Computing'
            }),
            'difficulty_level': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'status': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'short_description': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none text-sm',
                'placeholder': 'Short summary / tagline'
            }),
            'description': forms.Textarea(attrs={
                'rows': 4,
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none text-sm',
                'placeholder': 'Detailed syllabus and course deliverables breakdown...'
            }),
            'thumbnail': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none text-sm',
                'placeholder': 'genai.svg'
            }),
        }

    def clean_slug(self):
        from django.utils.text import slugify
        slug = self.cleaned_data.get('slug')
        title = self.cleaned_data.get('title')
        if not slug and title:
            slug = slugify(title)
        return slug


class LMSUserCreateForm(forms.Form):
    ROLE_CHOICES = [
        ('STUDENT', 'Student (Learner)'),
        ('MENTOR', 'Mentor / Instructor (Teacher)'),
        ('MANAGER', 'Academic Program Manager'),
        ('ADMIN', 'LMS Administrator'),
    ]

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none text-sm',
            'placeholder': 'user@example.com'
        }),
        required=True
    )
    first_name = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none text-sm',
            'placeholder': 'First Name'
        }),
        required=True
    )
    last_name = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none text-sm',
            'placeholder': 'Last Name'
        }),
        required=True
    )
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none text-sm'
        }),
        initial='STUDENT',
        required=True
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none text-sm',
            'placeholder': 'Default: AclMission@123'
        }),
        required=False,
        help_text="Leave blank to automatically use default password 'AclMission@123'"
    )
    specialization = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none text-sm',
            'placeholder': 'e.g. Agentic AI, Full-Stack Python, Distributed Systems'
        }),
        required=False
    )
    phone = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none text-sm',
            'placeholder': '+91 98765 43210'
        }),
        required=False
    )
    bio = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none text-sm',
            'placeholder': 'Academic or professional background summary...'
        }),
        required=False
    )
    courses_to_enroll = forms.ModelMultipleChoiceField(
        queryset=Course.objects.filter(is_active=True),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'rounded border-gray-300 text-purple-600 focus:ring-purple-500 mr-2'
        }),
        label="Associate / Join Courses immediately"
    )


class ModuleCreateForm(forms.ModelForm):
    class Meta:
        from .models import Module
        model = Module
        fields = ['course', 'title', 'description', 'order']
        widgets = {
            'course': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none text-sm',
                'placeholder': 'e.g. Module 4: Agent Memory & Vector Store Tooling'
            }),
            'description': forms.Textarea(attrs={
                'rows': 3,
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none text-sm',
                'placeholder': 'Module learning objectives and architectural scope...'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none text-sm'
            }),
        }


class LessonCreateForm(forms.ModelForm):
    class Meta:
        from .models import Lesson
        model = Lesson
        fields = ['module', 'title', 'lesson_type', 'duration_minutes', 'video_url', 'content', 'resource_link', 'order', 'is_required']
        widgets = {
            'module': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none text-sm',
                'placeholder': 'e.g. 4.1 Implementing ReAct Decision Loops'
            }),
            'lesson_type': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'duration_minutes': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'video_url': forms.URLInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none text-sm',
                'placeholder': 'https://youtube.com/watch?v=...'
            }),
            'content': forms.Textarea(attrs={
                'rows': 4,
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none text-sm',
                'placeholder': 'Reading guide, code snippets, and instructions...'
            }),
            'resource_link': forms.URLInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none text-sm',
                'placeholder': 'https://github.com/example/starter-lab'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none text-sm'
            }),
        }


class BatchForm(forms.ModelForm):
    name = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all outline-none text-sm font-semibold',
            'placeholder': 'e.g. AI Engineering & Autonomous Agents Cohort 2026'
        })
    )
    github_path = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all outline-none text-sm font-mono',
            'placeholder': 'e.g. https://github.com/apt-computing-labs/agentic-ai or org/repo'
        }),
        label="GitHub Path / Repository URL *"
    )
    gdrive_path = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all outline-none text-sm font-mono',
            'placeholder': 'e.g. https://drive.google.com/drive/folders/...'
        }),
        label="Google Drive Path / Resource Folder URL *"
    )
    zoom_link = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-rose-500 focus:border-transparent transition-all outline-none text-sm font-mono',
            'placeholder': 'e.g. https://zoom.us/j/9876543210 (Optional - add now or later)'
        }),
        label="Zoom / Google Meet Meeting Link (Optional)"
    )
    schedule_days = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all outline-none text-sm',
            'placeholder': 'e.g. Mon, Wed, Fri'
        }),
        label="Repetitive Days"
    )
    schedule_time = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all outline-none text-sm',
            'placeholder': 'e.g. 19:00 - 21:00 IST'
        }),
        label="Class Time"
    )
    schedule = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all outline-none text-sm',
            'placeholder': 'e.g. Every Mon, Wed, Fri from 19:00 to 21:00 IST'
        }),
        label="Recurring Schedule Summary"
    )
    code = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all outline-none text-sm uppercase font-mono',
            'placeholder': 'e.g. BATCH-2026-AI (Auto-generated if left blank)'
        }),
        label="Batch Code (Optional)"
    )
    status = forms.ChoiceField(
        choices=Batch.STATUS_CHOICES,
        required=False,
        initial='ONGOING',
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all outline-none text-sm'
        }),
        label="Batch Status"
    )
    auto_generate_sessions = forms.BooleanField(
        required=False,
        initial=True,
        label="Auto-generate upcoming live classes for the next 4 weeks based on this schedule & Zoom link"
    )

    class Meta:
        model = Batch
        fields = [
            'name', 'code', 'course', 'github_path', 'gdrive_path',
            'schedule_days', 'schedule_time', 'schedule', 'zoom_link',
            'start_date', 'end_date', 'status', 'description'
        ]
        widgets = {
            'course': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'start_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'end_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'description': forms.Textarea(attrs={
                'rows': 3,
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all outline-none text-sm',
                'placeholder': 'Batch objectives, schedule notes, and cohort guidelines...'
            }),
        }

    def clean_status(self):
        return self.cleaned_data.get('status') or 'ONGOING'

    def clean_github_path(self):
        val = (self.cleaned_data.get('github_path') or '').strip()
        if val and not val.startswith(('http://', 'https://', 'git@')):
            val = f"https://{val}"
        return val

    def clean_gdrive_path(self):
        val = (self.cleaned_data.get('gdrive_path') or '').strip()
        if val and not val.startswith(('http://', 'https://')):
            val = f"https://{val}"
        return val

    def clean_zoom_link(self):
        val = (self.cleaned_data.get('zoom_link') or '').strip()
        if val and not val.startswith(('http://', 'https://')):
            val = f"https://{val}"
        return val

    def clean_code(self):
        code = (self.cleaned_data.get('code') or '').strip().upper()
        name = self.cleaned_data.get('name', 'BATCH')
        if not code and name:
            import re, random
            base = re.sub(r'[^A-Za-z0-9]+', '-', name).strip('-').upper()[:12] or 'BATCH'
            code = f"{base}-{random.randint(100, 999)}"
            while Batch.objects.filter(code=code).exists():
                code = f"{base}-{random.randint(100, 999)}"
        return code

    def clean(self):
        cleaned_data = super().clean()
        schedule_days = cleaned_data.get('schedule_days')
        schedule_time = cleaned_data.get('schedule_time')
        schedule = cleaned_data.get('schedule')
        if not schedule and schedule_days:
            if schedule_time:
                cleaned_data['schedule'] = f"{schedule_days} @ {schedule_time}"
            else:
                cleaned_data['schedule'] = schedule_days
        return cleaned_data


class BatchAssignMembersForm(forms.Form):
    students = forms.ModelMultipleChoiceField(
        queryset=LMSUser.objects.filter(is_active=True).filter(role__in=['STUDENT', 'USER']).order_by('first_name', 'last_name', 'email'),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'rounded border-gray-300 text-indigo-600 focus:ring-indigo-500'
        }),
        label="Select Students to Add"
    )
    mentors = forms.ModelMultipleChoiceField(
        queryset=LMSUser.objects.filter(is_active=True, role='MENTOR').order_by('first_name', 'last_name', 'email'),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'rounded border-gray-300 text-purple-600 focus:ring-purple-500'
        }),
        label="Select Mentors / Faculty"
    )


class CohortUserEditForm(forms.ModelForm):
    batch = forms.ModelChoiceField(
        queryset=Batch.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm'
        }),
        empty_label="-- Select Batch / Cohort (Optional) --"
    )

    class Meta:
        model = LMSUser
        fields = ['first_name', 'last_name', 'email', 'role', 'phone', 'specialization', 'bio', 'is_active']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'role': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'specialization': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'bio': forms.Textarea(attrs={
                'rows': 3,
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'rounded border-gray-300 text-blue-600 focus:ring-blue-500'
            }),
        }


class AdminResetPasswordForm(forms.Form):
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-rose-500 focus:border-transparent transition-all outline-none text-sm',
            'placeholder': 'Enter new password'
        }),
        min_length=6,
        required=True
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-rose-500 focus:border-transparent transition-all outline-none text-sm',
            'placeholder': 'Confirm new password'
        }),
        min_length=6,
        required=True
    )

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('new_password')
        p2 = cleaned_data.get('confirm_password')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data


class StudentPaymentRecordForm(forms.ModelForm):
    class Meta:
        model = StudentPayment
        fields = [
            'student', 'batch', 'course', 'title', 'total_amount', 'amount_paid',
            'due_date', 'payment_status', 'payment_method', 'transaction_reference', 'notes'
        ]
        widgets = {
            'student': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'batch': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'course': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all outline-none text-sm',
                'placeholder': 'e.g. Tuition Fee - Full Course'
            }),
            'total_amount': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all outline-none text-sm',
                'placeholder': '0.00',
                'step': '0.01'
            }),
            'amount_paid': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all outline-none text-sm',
                'placeholder': '0.00',
                'step': '0.01'
            }),
            'due_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'payment_status': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'payment_method': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'transaction_reference': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all outline-none text-sm',
                'placeholder': 'UTR / UPI Transaction ID / Bank Reference'
            }),
            'notes': forms.Textarea(attrs={
                'rows': 2,
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all outline-none text-sm',
                'placeholder': 'Verification notes, receipt details, or installment terms...'
            }),
        }


class StudentPaymentSubmissionForm(forms.Form):
    payment_id = forms.IntegerField(widget=forms.HiddenInput())
    amount_paid = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all outline-none text-sm',
            'placeholder': 'Amount paid (e.g. 5000.00)',
            'step': '0.01'
        })
    )
    payment_method = forms.ChoiceField(
        choices=StudentPayment.PAYMENT_METHOD_CHOICES,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all outline-none text-sm'
        }),
        initial='UPI'
    )
    transaction_reference = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all outline-none text-sm',
            'placeholder': 'Enter UTR / UPI Transaction Reference (12 digits)'
        }),
        help_text="Provide the bank UTR or UPI Transaction ID after completing the transfer"
    )
    notes = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 2,
            'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all outline-none text-sm',
            'placeholder': 'Any additional remarks or transfer date notes...'
        }),
        required=False
    )


class BatchSessionForm(forms.ModelForm):
    class Meta:
        model = BatchSession
        fields = ['batch', 'title', 'instructor', 'scheduled_date', 'start_time', 'end_time', 'meeting_link', 'recording_link', 'status', 'agenda']
        widgets = {
            'batch': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm',
                'placeholder': 'e.g. Session 3: Multi-Agent Systems & State Graphs'
            }),
            'instructor': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'scheduled_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'start_time': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'end_time': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'meeting_link': forms.URLInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm',
                'placeholder': 'https://meet.google.com/... or https://zoom.us/j/...'
            }),
            'recording_link': forms.URLInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm',
                'placeholder': 'https://drive.google.com/... or YouTube link'
            }),
            'status': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'agenda': forms.Textarea(attrs={
                'rows': 3,
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none text-sm',
                'placeholder': 'Topics covered, prerequisites, and session deliverables...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'batch' in self.fields:
            self.fields['batch'].required = False


class BatchMaterialForm(forms.ModelForm):
    class Meta:
        model = BatchMaterial
        fields = ['batch', 'session', 'title', 'material_type', 'external_url', 'attachment_file', 'description']
        widgets = {
            'batch': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'session': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none text-sm',
                'placeholder': 'e.g. Architecture Slides / Starter Code Notebook'
            }),
            'material_type': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none text-sm'
            }),
            'external_url': forms.URLInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none text-sm',
                'placeholder': 'https://github.com/... or https://drive.google.com/...'
            }),
            'attachment_file': forms.FileInput(attrs={
                'class': 'w-full px-3 py-2 rounded-xl border border-gray-200 text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-bold file:bg-purple-50 file:text-purple-700 hover:file:bg-purple-100'
            }),
            'description': forms.Textarea(attrs={
                'rows': 2,
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none text-sm',
                'placeholder': 'Brief description of resource or download instructions...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'batch' in self.fields:
            self.fields['batch'].required = False


class BatchAssignmentForm(forms.ModelForm):
    ASSIGN_TARGET_CHOICES = [
        ('ALL', 'Send to All Students in Batch'),
        ('INDIVIDUAL', 'Assign to Specific Individual Student'),
    ]
    assign_target = forms.ChoiceField(
        choices=ASSIGN_TARGET_CHOICES,
        initial='ALL',
        widget=forms.RadioSelect(attrs={'class': 'accent-indigo-600'})
    )

    class Meta:
        model = BatchAssignment
        fields = ['batch', 'target_student', 'title', 'description', 'due_date', 'max_score', 'resource_url']
        widgets = {
            'batch': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 text-sm outline-none focus:ring-2 focus:ring-indigo-500'
            }),
            'target_student': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 text-sm outline-none focus:ring-2 focus:ring-indigo-500'
            }),
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 text-sm outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'e.g. Day 8 Milestone: Implement ReAct Agent Loop'
            }),
            'description': forms.Textarea(attrs={
                'rows': 4,
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 text-sm outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'Deliverables, acceptance criteria, architectural constraints...'
            }),
            'due_date': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 text-sm outline-none focus:ring-2 focus:ring-indigo-500'
            }),
            'max_score': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 text-sm outline-none focus:ring-2 focus:ring-indigo-500'
            }),
            'resource_url': forms.URLInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 text-sm outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'https://github.com/starter-code or notebook URL'
            }),
        }

    def __init__(self, *args, batch=None, **kwargs):
        super().__init__(*args, **kwargs)
        if 'batch' in self.fields:
            self.fields['batch'].required = False
        if 'target_student' in self.fields:
            self.fields['target_student'].required = False
            if batch:
                self.fields['target_student'].queryset = batch.students.filter(is_active=True)

