from django.db import models
from django.conf import settings
from core.models import BaseModel
from projects.models import Project, Sprint, Requirement
from django.contrib.contenttypes.fields import GenericRelation

class Task(BaseModel):
    """
    Task management module.
    """
    TASK_TYPES = [
        ('DEVELOPMENT', 'Development'),
        ('TESTING', 'Testing'),
        ('MAINTENANCE', 'Maintenance'),
    ]

    STATUS_CHOICES = [
        ('BACKLOG', 'Backlog'),
        ('PLANNED', 'Planned'),
        ('IN_PROGRESS', 'In Progress'),
        ('IN_REVIEW', 'In Review'),
        ('TESTING', 'Testing'),
        ('PENDING_APPROVAL', 'Pending Approval'),
        ('BLOCKED', 'Blocked'),
        ('CLOSED', 'Closed'),
        ('DEACTIVATED', 'Deactivated'),
    ]

    PRIORITY_CHOICES = [
        ('CRITICAL', 'Critical'),
        ('HIGH', 'High'),
        ('MEDIUM', 'Medium'),
        ('LOW', 'Low'),
    ]

    task_id = models.CharField(max_length=50, unique=True)
    task_type = models.CharField(max_length=20, choices=TASK_TYPES, default='DEVELOPMENT')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks')
    requirement = models.ForeignKey(Requirement, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks')
    sprint = models.ForeignKey(Sprint, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tasks')
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='reported_tasks')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='MEDIUM')
    story_points = models.IntegerField(default=0)
    hours_spent = models.DecimalField(max_digits=8, decimal_places=2, default=0.0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='BACKLOG')
    due_date = models.DateField(null=True, blank=True)
    actual_completion_date = models.DateField(null=True, blank=True)
    github_url = models.URLField(blank=True, null=True, help_text="Link to GitHub repository/PR")
    gdrive_url = models.URLField(blank=True, null=True, help_text="Link to Google Drive documents")
    attachments = GenericRelation('core.Attachment')

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.task_type in ['DEVELOPMENT', 'TESTING'] and not self.requirement:
            raise ValidationError({'requirement': 'A Requirement must be provided for Development and Testing tasks.'})
        super().clean()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_state = self._get_current_state()

    def _get_current_state(self):
        return {
            'title': self.__dict__.get('title'),
            'status': self.__dict__.get('status'),
            'priority': self.__dict__.get('priority'),
            'assignee_id': self.__dict__.get('assignee_id'),
            'story_points': self.__dict__.get('story_points'),
            'due_date': self.__dict__.get('due_date'),
        }

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        from core.models import AuditLog
        
        if is_new:
            AuditLog.objects.create(
                action='CREATE',
                model_name='Task',
                object_id=str(self.pk),
                user=self.created_by,
                changes={'event': 'Task created'}
            )
        else:
            current_state = self._get_current_state()
            changes = {}
            for field, old_value in self._original_state.items():
                new_value = current_state[field]
                if old_value != new_value:
                    changes[field] = {
                        'old': str(old_value) if old_value is not None else 'None', 
                        'new': str(new_value) if new_value is not None else 'None'
                    }
            
            # Check for edit comment
            if hasattr(self, '_edit_comment') and self._edit_comment:
                changes['edit_comment'] = {'old': '', 'new': self._edit_comment}
            
            if changes:
                user = getattr(self, 'updated_by', None) or getattr(self, 'created_by', None)
                AuditLog.objects.create(
                    action='UPDATE',
                    model_name='Task',
                    object_id=str(self.pk),
                    user=user,
                    changes=changes
                )
            
        self._original_state = self._get_current_state()
        
        # Check if requirement should be closed
        if self.requirement:
            # Re-fetch tasks from DB to get the latest status of this task as well
            if not self.requirement.tasks.exclude(status='CLOSED').exists():
                if self.requirement.status != 'CLOSED':
                    self.requirement.status = 'CLOSED'
                    self.requirement.save()

    def __str__(self):
        return f"[{self.task_id}] {self.title}"

class TaskComment(BaseModel):
    """
    Comments on tasks.
    """
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='task_comments')
    content = models.TextField()

    def __str__(self):
        return f"Comment by {self.author} on {self.task.task_id}"
