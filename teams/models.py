from django.db import models
from django.conf import settings
from core.models import BaseModel

class Team(BaseModel):
    """
    Team definitions: Architecture, Development, Testing, etc.
    """
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    lead = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='led_teams')
    capacity = models.DecimalField(max_digits=5, decimal_places=2, default=0.0, help_text="Total team capacity in story points or hours")
    velocity = models.DecimalField(max_digits=5, decimal_places=2, default=0.0, help_text="Average team velocity")

    def __str__(self):
        return self.name

class TeamMember(BaseModel):
    """
    Mapping users to teams.
    """
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='team_memberships')
    joined_date = models.DateField(auto_now_add=True)
    is_active_member = models.BooleanField(default=True)

    class Meta:
        unique_together = ('team', 'user')

    def __str__(self):
        return f"{self.user} - {self.team}"

class TeamMessage(BaseModel):
    """
    Messages sent within a team channel.
    """
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_team_messages')
    content = models.TextField()

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Message from {self.sender} in {self.team}"
