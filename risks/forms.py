from django import forms
from .models import Risk

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class RiskForm(forms.ModelForm):
    attachments = forms.FileField(
        widget=MultipleFileInput(attrs={'multiple': True}),
        required=False,
        help_text="Upload multiple files or images to attach to this risk."
    )

    class Meta:
        model = Risk
        fields = ['project', 'title', 'description', 'probability', 'impact', 'owner', 'mitigation_plan']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'mitigation_plan': forms.Textarea(attrs={'rows': 4}),
        }
