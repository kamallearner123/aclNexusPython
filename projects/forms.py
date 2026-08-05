from django import forms
from .models import Project, Requirement

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class ProjectForm(forms.ModelForm):
    from core.models import User
    
    client = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=False,
        label="Client",
        empty_label="---------"
    )
    
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from core.models import User
        self.fields['client'].queryset = User.objects.filter(roles__name='Client')
        
        if self.instance and self.instance.pk:
            first_client = self.instance.clients.first()
            if first_client:
                self.initial['client'] = first_client.pk

    def save(self, commit=True):
        project = super().save(commit=False)
        selected_client = self.cleaned_data.get('client')
        
        if selected_client:
            project.client = selected_client.email
        else:
            project.client = ''
            
        if commit:
            project.save()
            self.save_m2m()
            project.clients.clear()
            if selected_client:
                project.clients.add(selected_client)
        return project
class RequirementForm(forms.ModelForm):
    class Meta:
        model = Requirement
        fields = [
            'project',
            'title',
            'description',
            'start_date',
            'end_date',
            'estimated_effort',
            'effort_spent',
            'status',
            'priority',
            'owner',
        ]

        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }
