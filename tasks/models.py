from django.db import models
from django.conf import settings
from core.models import BaseModel
from projects.models import Project, Sprint
from django.contrib.contenttypes.fields import GenericRelation

class Task(BaseModel):
    """
    Task management module.
    """
    STATUS_CHOICES = [
        ('BACKLOG', 'Backlog'),
        ('PLANNED', 'Planned'),
        ('IN_PROGRESS', 'In Progress'),
        ('IN_REVIEW', 'In Review'),
        ('TESTING', 'Testing'),
        ('BLOCKED', 'Blocked'),
        ('COMPLETED', 'Completed'),
    ]

    PRIORITY_CHOICES = [
        ('CRITICAL', 'Critical'),
        ('HIGH', 'High'),
        ('MEDIUM', 'Medium'),
        ('LOW', 'Low'),
    ]

    task_id = models.CharField(max_length=50, unique=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks')
    sprint = models.ForeignKey(Sprint, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tasks')
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='reported_tasks')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='MEDIUM')
    story_points = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='BACKLOG')
    due_date = models.DateField(null=True, blank=True)
    actual_completion_date = models.DateField(null=True, blank=True)
    github_url = models.URLField(blank=True, null=True, help_text="Link to GitHub repository/PR")
    gdrive_url = models.URLField(blank=True, null=True, help_text="Link to Google Drive documents")
    attachments = GenericRelation('core.Attachment')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_state = self._get_current_state()

    def _get_current_state(self):
        return {
            'title': getattr(self, 'title', None),
            'status': getattr(self, 'status', None),
            'priority': getattr(self, 'priority', None),
            'assignee_id': getattr(self, 'assignee_id', None),
            'story_points': getattr(self, 'story_points', None),
            'due_date': getattr(self, 'due_date', None),
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
