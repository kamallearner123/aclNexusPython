from django.db import models
from core.models import BaseModel
from projects.models import Project
from tasks.models import Task
from django.contrib.contenttypes.fields import GenericRelation

class Issue(BaseModel):
    """
    Issue management module.
    """
    ISSUE_TYPES = [
        ('BUG', 'Bug'),
        ('INCIDENT', 'Incident'),
        ('DEFECT', 'Defect'),
        ('SECURITY', 'Security Finding'),
        ('PRODUCTION', 'Production Issue'),
    ]

    SEVERITY_CHOICES = [
        ('CRITICAL', 'Critical'),
        ('MAJOR', 'Major'),
        ('MINOR', 'Minor'),
        ('TRIVIAL', 'Trivial'),
    ]

    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('IN_PROGRESS', 'In Progress'),
        ('RESOLVED', 'Resolved'),
        ('CLOSED', 'Closed'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='issues')
    task = models.ForeignKey(Task, on_delete=models.SET_NULL, null=True, blank=True, related_name='issues')
    title = models.CharField(max_length=255)
    issue_type = models.CharField(max_length=20, choices=ISSUE_TYPES)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    impact = models.TextField(blank=True)
    root_cause = models.TextField(blank=True)
    resolution = models.TextField(blank=True)
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
            'severity': getattr(self, 'severity', None),
            'issue_type': getattr(self, 'issue_type', None),
        }

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        from core.models import AuditLog
        
        if is_new:
            AuditLog.objects.create(
                action='CREATE',
                model_name='Issue',
                object_id=str(self.pk),
                user=self.created_by,
                changes={'event': 'Issue created'}
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
                    model_name='Issue',
                    object_id=str(self.pk),
                    user=user,
                    changes=changes
                )
            
        self._original_state = self._get_current_state()

    def __str__(self):
        return f"[{self.get_issue_type_display()}] {self.title}"
