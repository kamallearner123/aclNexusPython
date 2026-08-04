from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Role, NoteTopic, Note, ClientProfile
from teams.models import Team
from projects.models import Project

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class NoteTopicForm(forms.ModelForm):
    class Meta:
        model = NoteTopic
        fields = ['name']

class NoteForm(forms.ModelForm):
    topic = forms.ModelChoiceField(
        queryset=NoteTopic.objects.none(),
        required=False,
        empty_label="Uncategorized"
    )
    attachments = forms.FileField(
        widget=MultipleFileInput(attrs={'multiple': True}),
        required=False,
        help_text="Upload multiple files or images to attach to this note."
    )

    class Meta:
        model = Note
        fields = ['topic', 'title', 'content']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # We will set the queryset in the view, but we can also set required=False here just in case.
        self.fields['topic'].required = False

class EmployeeCreationForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    roles = forms.ModelMultipleChoiceField(
        queryset=Role.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        help_text="Select one or more roles for this employee."
    )

    teams = forms.ModelMultipleChoiceField(
        queryset=Team.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('email', 'first_name', 'last_name', 'roles', 'teams')

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            self.save_m2m() # saves roles
            from teams.models import TeamMember
            TeamMember.objects.filter(user=user).delete()
            for team in self.cleaned_data.get('teams', []):
                TeamMember.objects.create(user=user, team=team)
        return user

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name')

class ProfileEditForm(forms.ModelForm):
    topic_1 = forms.CharField(required=False, max_length=50, label="Topic 1")
    topic_2 = forms.CharField(required=False, max_length=50, label="Topic 2")
    topic_3 = forms.CharField(required=False, max_length=50, label="Topic 3")
    topic_4 = forms.CharField(required=False, max_length=50, label="Topic 4")
    topic_5 = forms.CharField(required=False, max_length=50, label="Topic 5")

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'avatar')
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            topics = self.instance.interested_topics.split(',') if self.instance.interested_topics else []
            for i, topic in enumerate(topics):
                if i < 5:
                    self.fields[f'topic_{i+1}'].initial = topic.strip()
                    
    def save(self, commit=True):
        user = super().save(commit=False)
        topics = []
        for i in range(1, 6):
            topic = self.cleaned_data.get(f'topic_{i}')
            if topic and topic.strip():
                topics.append(topic.strip())
        user.interested_topics = ','.join(topics)
        if commit:
            user.save()
        return user

class EmployeeEditForm(forms.ModelForm):
    roles = forms.ModelMultipleChoiceField(
        queryset=Role.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        help_text="Select one or more roles for this employee."
    )
    teams = forms.ModelMultipleChoiceField(
        queryset=Team.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text="Select one or more teams for this employee."
    )

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'roles', 'teams')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['teams'].initial = self.instance.teams.all()

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            self.save_m2m() # saves roles
            from teams.models import TeamMember
            TeamMember.objects.filter(user=user).delete()
            for team in self.cleaned_data.get('teams', []):
                TeamMember.objects.create(user=user, team=team)
        return user

class ClientCreationForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    company_name = forms.CharField(max_length=255, required=False)
    phone = forms.CharField(max_length=50, required=False)
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)
    projects = forms.ModelMultipleChoiceField(
        queryset=Project.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text="Select projects to assign to this client."
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('email', 'first_name', 'last_name')

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            client_role, _ = Role.objects.get_or_create(name='Client')
            user.roles.add(client_role)
            
            ClientProfile.objects.create(
                user=user,
                company_name=self.cleaned_data.get('company_name', ''),
                phone=self.cleaned_data.get('phone', ''),
                address=self.cleaned_data.get('address', '')
            )
            
            for project in self.cleaned_data.get('projects', []):
                project.clients.add(user)
                
        return user

class ClientEditForm(forms.ModelForm):
    company_name = forms.CharField(max_length=255, required=False)
    phone = forms.CharField(max_length=50, required=False)
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)
    projects = forms.ModelMultipleChoiceField(
        queryset=Project.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text="Select projects to assign to this client."
    )

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            profile = getattr(self.instance, 'client_profile', None)
            if profile:
                self.fields['company_name'].initial = profile.company_name
                self.fields['phone'].initial = profile.phone
                self.fields['address'].initial = profile.address
            self.fields['projects'].initial = Project.objects.filter(clients=self.instance)

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            profile, _ = ClientProfile.objects.get_or_create(user=user)
            profile.company_name = self.cleaned_data.get('company_name', '')
            profile.phone = self.cleaned_data.get('phone', '')
            profile.address = self.cleaned_data.get('address', '')
            profile.save()
            
            for p in Project.objects.filter(clients=user):
                p.clients.remove(user)
            for p in self.cleaned_data.get('projects', []):
                p.clients.add(user)
                
        return user
