from django.db import models
from django.conf import settings
from core.models import BaseModel
from projects.models import Project

class Risk(BaseModel):
    """
    Risk management module.
    """
    PROBABILITY_CHOICES = [
        (1, 'Low'),
        (2, 'Medium'),
        (3, 'High'),
    ]

    IMPACT_CHOICES = [
        (1, 'Low'),
        (2, 'Medium'),
        (3, 'High'),
        (4, 'Critical'),
    ]

    RISK_LEVEL_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]

    risk_id = models.CharField(max_length=50, unique=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='risks')
    title = models.CharField(max_length=255)
    description = models.TextField()
    probability = models.IntegerField(choices=PROBABILITY_CHOICES)
    impact = models.IntegerField(choices=IMPACT_CHOICES)
    risk_score = models.IntegerField(help_text="Calculated as Probability x Impact", default=0)
    risk_level = models.CharField(max_length=20, choices=RISK_LEVEL_CHOICES, blank=True)
    mitigation_plan = models.TextField(blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='owned_risks')

    def save(self, *args, **kwargs):
        self.risk_score = self.probability * self.impact
        if self.risk_score >= 12:
            self.risk_level = 'CRITICAL'
        elif self.risk_score >= 8:
            self.risk_level = 'HIGH'
        elif self.risk_score >= 4:
            self.risk_level = 'MEDIUM'
        else:
            self.risk_level = 'LOW'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.risk_id}] {self.title}"
