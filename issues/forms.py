from django import forms
from .models import Issue

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class IssueForm(forms.ModelForm):
    edit_comment = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'Optional: Describe the reason for this edit...'}),
        required=False,
        help_text="Provide context for this change. It will appear in the activity history."
    )

    attachments = forms.FileField(
        widget=MultipleFileInput(attrs={'multiple': True}),
        required=False,
        help_text="Upload multiple files or images to attach to this issue."
    )

    class Meta:
        model = Issue
        fields = ['project', 'task', 'title', 'issue_type', 'severity', 'status', 'impact', 'root_cause', 'resolution', 'github_url', 'gdrive_url', 'edit_comment']
        widgets = {
            'impact': forms.Textarea(attrs={'rows': 3}),
            'root_cause': forms.Textarea(attrs={'rows': 3}),
            'resolution': forms.Textarea(attrs={'rows': 3}),
        }
