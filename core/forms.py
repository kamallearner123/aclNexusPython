from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Role, NoteTopic, Note

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

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('email', 'first_name', 'last_name', 'roles', 'team')

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name')

class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'interested_topics', 'avatar')
