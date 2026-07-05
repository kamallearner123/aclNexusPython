from django import forms
from .models import Risk

class RiskForm(forms.ModelForm):
    class Meta:
        model = Risk
        fields = ['project', 'title', 'description', 'probability', 'impact', 'owner', 'mitigation_plan']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'mitigation_plan': forms.Textarea(attrs={'rows': 4}),
        }
