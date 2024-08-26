# models.py
from django.db import models

class Users(models.Model):
    username = models.CharField(max_length=100, null= True)
    user_email = models.EmailField(null= True)
    role = models.CharField(max_length=100, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default='True',null=True)

class AuditLog(models.Model):
    event = models.CharField(max_length=255)
    action_user = models.ForeignKey(Users, on_delete=models.PROTECT, null=True,  related_name='action_user_auditlogs')
    target_user = models.ForeignKey(Users, on_delete=models.PROTECT, related_name='target_user_auditlogs', null= True)
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.event} - {self.action_user} - {self.created_at}"

class Checklist(models.Model):
    CHECKLIST_TYPES = (
        ('daily', 'Information Security Daily Checklist'),
        ('privileged', 'Privileged Account Monitoring Checklist'),
    )

   
    checklist_type = models.CharField(max_length=255, choices=CHECKLIST_TYPES)
    reviewer = models.ForeignKey(Users, on_delete=models.PROTECT, related_name='reviewed_checklists')
    uploaded_by = models.ForeignKey(Users, on_delete=models.PROTECT, related_name='uploaded_checklists')
    file = models.FileField(upload_to='static/checklists')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    

class Comment(models.Model):
    checklist = models.ForeignKey(Checklist, on_delete=models.CASCADE, related_name='comments')
    signed_file = models.FileField(upload_to='static/checklists_signed', null=True, blank=True )
    comment = models.TextField(blank=True)
    #signature = models.ImageField(upload_to='signatures', null=True, blank=True)
    reviewer = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='comments')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

