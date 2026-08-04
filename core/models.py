import uuid
from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation

class BaseModel(models.Model):
    """
    Abstract base model with fields required across all tables.
    """
    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Using string reference to 'core.User' to avoid circular imports later
    created_by = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True, blank=True, related_name="%(app_label)s_%(class)s_created")
    updated_by = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True, blank=True, related_name="%(app_label)s_%(class)s_updated")
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True

class Role(BaseModel):
    """
    Role definitions for RBAC.
    Examples: Project Manager, Team Lead, Engineer.
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_('The Email field must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))

        return self.create_user(email, password, **extra_fields)

class User(AbstractUser, BaseModel):
    """
    Custom User model using email as the primary identifier and incorporating BaseModel.
    """
    username = None # Remove username field
    email = models.EmailField(_('email address'), unique=True)
    
    roles = models.ManyToManyField(Role, blank=True, related_name='users')
    teams = models.ManyToManyField('teams.Team', through='teams.TeamMember', through_fields=('user', 'team'), blank=True, related_name='core_users')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    
    # AI Daily Tech News fields
    interested_topics = models.CharField(max_length=255, blank=True, help_text="Comma-separated topics of interest")
    daily_news_cache = models.JSONField(default=list, blank=True)
    news_last_fetched = models.DateField(null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    @property
    def is_client(self):
        return self.roles.filter(name='Client').exists()

    def __str__(self):
        return self.email

class AuditLog(models.Model):
    """
    Tracks changes made to models.
    """
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
    ]

    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    changes = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.action} on {self.model_name} ({self.object_id}) by {self.user}"

class Attachment(models.Model):
    """
    Generic Attachment model that can be linked to any object (Project, Task, Issue).
    """
    file = models.FileField(upload_to='attachments/%Y/%m/%d/')
    filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Generic relation fields
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=50)
    content_object = GenericForeignKey('content_type', 'object_id')

    def __str__(self):
        return self.filename

class NoteTopic(BaseModel):
    """
    Topic category for personal user notes.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='note_topics')
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class Note(BaseModel):
    """
    Personal user note.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notes')
    topic = models.ForeignKey(NoteTopic, on_delete=models.SET_NULL, null=True, blank=True, related_name='notes')
    title = models.CharField(max_length=255)
    content = models.TextField()
    attachments = GenericRelation('core.Attachment')

    def __str__(self):
        return self.title

class NoteEntry(BaseModel):
    """
    An additional entry or update appended to an existing note.
    """
    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name='entries')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    
    def __str__(self):
        return f"Entry on {self.note.title}"

class ClientProfile(BaseModel):
    """
    Client specific details.
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='client_profile')
    company_name = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)

    def __str__(self):
        return f"{self.company_name} ({self.user.email})"

