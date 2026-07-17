from django import forms
from .models import Project

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class ProjectForm(forms.ModelForm):
    attachments = forms.FileField(
        widget=MultipleFileInput(attrs={'multiple': True}),
        required=False,
        help_text="Upload multiple files or images to attach to this project."
    )

    class Meta:
        model = Project
        fields = ['name', 'code', 'description', 'status', 'priority', 'project_type', 
                  'client', 'category', 'owner', 'teams', 'start_date', 'end_date', 'budget',
                  'github_url', 'gdrive_url']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
        }
