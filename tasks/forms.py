from django import forms
from .models import Task

class TaskForm(forms.ModelForm):

    edit_comment = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'Optional: Describe the reason for this edit...'}),
        required=False,
        help_text="Provide context for this change. It will appear in the activity history."
    )

    class Meta:
        model = Task
        fields = ['task_id', 'project', 'sprint', 'title', 'description', 'assignee', 'priority', 'story_points', 'status', 'due_date', 'github_url', 'gdrive_url', 'edit_comment']
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
        }
