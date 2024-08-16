# models.py
from django.db import models

class Users(models.Model):
    username = models.CharField(max_length=100, null= True)
    user_email = models.EmailField(null= True)
    role = models.CharField(max_length=100, null=True)

class Checklist(models.Model):
    CHECKLIST_TYPES = (
        ('daily', 'Information Security Daily Checklist'),
        ('privileged', 'Privileged Account Monitoring Checklist'),
    )

   
    checklist_type = models.CharField(max_length=255, choices=CHECKLIST_TYPES)
    reviewer = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='reviewed_checklists')
    uploaded_by = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='uploaded_checklists')
    file = models.FileField(upload_to='static/checklists')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Comment(models.Model):
    checklist = models.ForeignKey(Checklist, on_delete=models.CASCADE, related_name='comments')
    
    comment = models.TextField(blank=True)
    signature = models.ImageField(upload_to='signatures', null=True, blank=True)
    reviewer = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='comments')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

