from django.db import models
from django.conf import settings
from core.models import BaseModel
from django.contrib.contenttypes.fields import GenericRelation

class Project(BaseModel):
    """
    Project definitions
    """
    PROJECT_TYPES = [
        ('AUTOMATION', 'Automation'),
        ('PRODUCT', 'Product Development'),
        ('SECURITY', 'Cyber Security'),
        ('AI', 'AI Platform'),
        ('RESEARCH', 'Research'),
        ('INTERNAL', 'Internal'),
        ('AGENTIC_AI', 'Agentic AI'),
        ('AUTOMOTIVE', 'Automotive'),
    ]

    STATUS_CHOICES = [
        ('PLANNED', 'Planned'),
        ('ACTIVE', 'Active'),
        ('ON_HOLD', 'On Hold'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    PRIORITY_CHOICES = [
        ('CRITICAL', 'Critical'),
        ('HIGH', 'High'),
        ('MEDIUM', 'Medium'),
        ('LOW', 'Low'),
    ]

    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    client = models.CharField(max_length=255, blank=True)
    category = models.CharField(max_length=100, blank=True)
    project_type = models.CharField(max_length=20, choices=PROJECT_TYPES)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PLANNED')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='MEDIUM')
    budget = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    github_url = models.URLField(blank=True, null=True, help_text="Link to GitHub repository")
    gdrive_url = models.URLField(blank=True, null=True, help_text="Link to Google Drive folder (containing Requirement, Design, Implementation, Testing, Deployment)")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='owned_projects')
    teams = models.ManyToManyField('teams.Team', blank=True, related_name='projects')
    clients = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='client_projects')
    attachments = GenericRelation('core.Attachment')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_state = self._get_current_state()

    def _get_current_state(self):
        return {
            'name': self.__dict__.get('name'),
            'status': self.__dict__.get('status'),
            'priority': self.__dict__.get('priority'),
            'owner_id': self.__dict__.get('owner_id'),
            'budget': self.__dict__.get('budget'),
            'start_date': self.__dict__.get('start_date'),
            'end_date': self.__dict__.get('end_date'),
        }

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        
        # If the project is new, we don't have a PK yet, so we must call super().save() first
        # to generate the database ID before we can use it for task creation or audit logs.
        super().save(*args, **kwargs)
        
        from core.models import AuditLog
        
        if is_new:
            AuditLog.objects.create(
                action='CREATE',
                model_name='Project',
                object_id=str(self.pk),
                user=self.created_by,
                changes={'event': 'Project created'}
            )
            
            # Auto-generate process board for Automotive projects
            if self.project_type == 'AUTOMOTIVE':
                from tasks.models import Task
                from projects.models import Milestone
                
                date_str = self.created_at.strftime('%m%y')
                
                process_groups = [
                    ("ASPICE", [
                        "SYS.1 System Requirements Analysis",
                        "SYS.2 System Architectural Design",
                        "SYS.3 System Integration and Integration Test",
                        "SYS.4 System Qualification Test",
                        "SWE.1 Software Requirements Analysis",
                        "SWE.2 Software Architectural Design",
                        "SWE.3 Software Detailed Design and Unit Construction",
                        "SWE.4 Software Unit Verification",
                        "SWE.5 Software Integration and Integration Test",
                        "SWE.6 Software Qualification Test",
                    ]),
                    ("Cybersecurity", [
                        "CYB.1 Asset Identification",
                        "CYB.2 Threat Analysis and Risk Assessment (TARA)",
                        "CYB.3 Cybersecurity Goals",
                        "CYB.4 Cybersecurity Requirements",
                        "CYB.5 Cybersecurity Architecture",
                        "CYB.6 Cybersecurity Verification",
                        "CYB.7 Cybersecurity Validation",
                        "CYB.8 Incident Monitoring",
                    ]),
                    ("AUTOSAR", [
                        "AUTOSAR System Design",
                        "SWC Design",
                        "RTE Design",
                        "Communication Design",
                        "Diagnostics Design",
                        "Security Design",
                        "Integration Design",
                    ]),
                    ("Project Management", [
                        "Collect Requirements",
                        "PI Planning",
                        "Sprint Planning",
                        "Release Management",
                    ])
                ]
                
                task_idx = 1
                for group_name, processes in process_groups:
                    for process in processes:
                        # Create a milestone for each process
                        milestone = Milestone.objects.create(
                            project=self,
                            name=f"[{group_name}] {process}",
                            description=f"Process board area for {group_name} - {process}",
                            target_date=self.end_date if self.end_date else self.created_at.date(),
                            created_by=self.created_by,
                            updated_by=self.created_by
                        )
                        
                        # Create an initial default task to start the process
                        custom_task_id = f"AUTO{self.pk}{date_str}_Task_{task_idx}"
                        task_idx += 1
                        
                        Task.objects.create(
                            task_id=custom_task_id,
                            project=self,
                            title=f"Execute: {process}",
                            description=f"Initial task to begin {process} under {group_name}.",
                            status='BACKLOG',
                            priority='HIGH',
                            created_by=self.created_by,
                            updated_by=self.created_by
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
            
            if changes:
                user = getattr(self, 'updated_by', None) or getattr(self, 'created_by', None)
                AuditLog.objects.create(
                    action='UPDATE',
                    model_name='Project',
                    object_id=str(self.pk),
                    user=user,
                    changes=changes
                )
            
        self._original_state = self._get_current_state()

    def __str__(self):
        return f"[{self.code}] {self.name}"

    @property
    def requirements_stats(self):
        reqs = self.requirements.all()
        return {
            'completed': reqs.filter(status='CLOSED').count(),
            'inprogress': reqs.filter(status__in=['REVIEW', 'APPROVED', 'CONVERTED']).count(),
            'created': reqs.exclude(status__in=['CLOSED', 'REJECTED']).count()
        }

    @property
    def tasks_stats(self):
        tasks = self.tasks.all()
        return {
            'completed': tasks.filter(status='CLOSED').count(),
            'inprogress': tasks.filter(status__in=['IN_PROGRESS', 'REVIEW']).count(),
            'created': tasks.exclude(status__in=['CLOSED']).count()
        }

    @property
    def completion_percentage(self):
        tasks = self.tasks.all()
        total = tasks.count()
        if total == 0:
            return 0
        completed = tasks.filter(status='CLOSED').count()
        return int((completed / total) * 100)

class Milestone(BaseModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='milestones')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    target_date = models.DateField()
    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.project.code} - {self.name}"

class Sprint(BaseModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='sprints')
    name = models.CharField(max_length=150)
    goal = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    capacity = models.DecimalField(max_digits=5, decimal_places=2, default=0.0, help_text="Total sprint capacity in story points or hours")

    def __str__(self):
        return f"{self.project.code} - {self.name}"

class Requirement(BaseModel):
    """
    Client requirements for a project.
    """

    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('REVIEW', 'In Review'),
        ('APPROVED', 'Approved'),
        ('CONVERTED', 'Converted to Tasks'),
        ('CLOSED', 'Closed'),
        ('REJECTED', 'Rejected'),
        ('DEACTIVATED', 'Deactivated'),
    ]

    PRIORITY_CHOICES = [
        ('CRITICAL', 'Critical'),
        ('HIGH', 'High'),
        ('MEDIUM', 'Medium'),
        ('LOW', 'Low'),
    ]

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='requirements'
    )
    
    requirement_id = models.CharField(max_length=50, blank=True)
    phase = models.CharField(max_length=100, blank=True)
    dependency = models.CharField(max_length=255, blank=True)

    title = models.CharField(max_length=255)

    description = models.TextField()

    start_date = models.DateField(
        null=True,
        blank=True
    )

    end_date = models.DateField(
        null=True,
        blank=True
    )

    estimated_effort = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0
    )

    effort_spent = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT'
    )

    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='MEDIUM'
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='owned_requirements'
    )

    
    attachments = GenericRelation('core.Attachment')

    @property
    def total_hours_spent(self):
        from django.db.models import Sum
        total = self.tasks.aggregate(Sum('hours_spent'))['hours_spent__sum']
        return total or 0.0

    @property
    def readiness_score(self):
        total_tasks = self.tasks.count()
        if total_tasks == 0:
            return 0
        completed_tasks = self.tasks.filter(status='CLOSED').count()
        return int((completed_tasks / total_tasks) * 100)

    def save(self, *args, **kwargs):
        is_deactivated = False
        if self.pk:
            old_instance = Requirement.objects.get(pk=self.pk)
            if self.status == 'DEACTIVATED' and old_instance.status != 'DEACTIVATED':
                is_deactivated = True
        
        super().save(*args, **kwargs)
        
        if is_deactivated:
            for task in self.tasks.all():
                task.status = 'DEACTIVATED'
                task.save()

    def __str__(self):
        return f"Req: {self.title} ({self.project.code})"