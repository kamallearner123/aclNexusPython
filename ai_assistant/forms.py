from django import forms

from projects.models import Project

from .agent import REPORT_PRESETS
from .tools import get_accessible_projects


class PIAAnalysisForm(forms.Form):
    report_type = forms.ChoiceField(
        choices=[(key, value['label']) for key, value in REPORT_PRESETS.items()],
        initial='project_health',
    )
    project = forms.ModelChoiceField(
        queryset=Project.objects.none(),
        required=False,
        empty_label='Portfolio / auto-select',
    )
    prompt = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 4,
            'placeholder': 'Ask PIA for a project health assessment, sprint report, workload analysis, risk review, or weekly summary...',
        }),
        required=False,
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields['project'].queryset = get_accessible_projects(user)
