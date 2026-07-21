from django import forms
from .models import Task

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class TaskForm(forms.ModelForm):

    edit_comment = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'Optional: Describe the reason for this edit...'}),
        required=False,
        help_text="Provide context for this change. It will appear in the activity history."
    )

    attachments = forms.FileField(
        widget=MultipleFileInput(attrs={'multiple': True}),
        required=False,
        help_text="Upload multiple files or images to attach to this task."
    )

    class Meta:
        model = Task
        fields = ['task_id', 'project', 'sprint', 'title', 'description', 'assignee', 'priority', 'story_points', 'status', 'due_date', 'github_url', 'gdrive_url', 'edit_comment']
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.initial.get('project') or (self.instance and self.instance.pk and self.instance.project_id):
            self.fields['project'].disabled = True
