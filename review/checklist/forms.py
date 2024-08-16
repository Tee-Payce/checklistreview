# forms.py
from django import forms
from .models import Checklist, Users, Comment

class ChecklistForm(forms.ModelForm):
    reviewer = forms.ModelChoiceField(
        queryset=Users.objects.filter(role='reviewer'),
        label='Reviewer',
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Checklist
        fields = ['checklist_type', 'reviewer', 'file']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['reviewer'].label_from_instance = lambda obj: f"{obj.user_email}"

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['comment', 'signature']