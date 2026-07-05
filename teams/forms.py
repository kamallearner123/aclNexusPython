from django import forms
from .models import Team, TeamMember
from core.models import User

class TeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ['name', 'description', 'lead', 'capacity', 'velocity']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class TeamMemberForm(forms.ModelForm):
    class Meta:
        model = TeamMember
        fields = ['user', 'is_active_member']
        widgets = {
            'user': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        team = kwargs.pop('team', None)
        super().__init__(*args, **kwargs)
        if team:
            # Exclude users already in the team
            existing_members = team.members.values_list('user_id', flat=True)
            self.fields['user'].queryset = User.objects.exclude(id__in=existing_members).filter(is_active=True)
