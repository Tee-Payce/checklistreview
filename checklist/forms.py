# forms.py
from django import forms
from .models import Checklist, Users, Comment

class ChecklistForm(forms.ModelForm):
    reviewer = forms.ModelChoiceField(
        queryset=Users.objects.filter(role='reviewer'),
        label='Reviewer',
        required=True,
        widget=forms.Select(attrs={'class': 'form-control','rows': 1, 'style' : 'width:30%; margin-left:35%;border:1px solid #4962A9; '})
    )

    class Meta:
        model = Checklist
        fields = ['checklist_type', 'reviewer', 'file']
        widgets = {
            'checklist_type' : forms.Select(attrs={'class': 'form-control', 'rows': 1, 'style' : 'width:30%; margin-left:35%;border:1px solid #4962A9; '}),

         }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['reviewer'].label_from_instance = lambda obj: f"{obj.user_email}"

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['comment', 'signed_file']
        widgets = {
            'comment' : forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'style' : 'width:30%; margin-left:35%;border:1px solid #4962A9; '}),
         }
        
class UsersForm(forms.ModelForm):
   
    role = forms.ChoiceField(
        label='Role',
        choices=[('editor', 'editor'), ('reviewer', 'reviewer')],
        widget=forms.Select(attrs={'class': 'form-control', 'rows': 1}),
       
    )
    
    class Meta:
        model = Users
        fields = ['id','username', 'user_email','role']
        labels = {'username': 'Username', 'user_email': 'User email'}
        widgets = {'username': forms.Textarea(attrs={'class': 'form-control', 'rows': 1}),
               'id':forms.HiddenInput(),
                   'user_email': forms.EmailInput(attrs={'class': 'form-control', 'rows': 1}),
                   }