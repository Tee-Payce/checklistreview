from django.urls import path
from checklist import views
from django.contrib.auth import views as auth_views

app_name = 'checklist'

urlpatterns = [
    path('login/', views.login_view, name='login_view'),
    #path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),  
    path('checklist-upload/<int:user_id>', views.checklist_editor, name= 'checklist_editor'),
    path('checklist-review/<int:checklist_id>', views.checklist_reviewer, name= 'checklist_reviewer'),
    path('audit-trail/<int:action_user>', views.audit_trail, name='audit_trail'),
    path('admin-audit/<int:action_user>', views.admin_audit, name='admin_audit'),
    path('delete-user/<int:user_id>/<int:action_user_id>', views.delete_user, name='delete_user'),
    path('user-management/<int:action_user>', views.users_mgmt, name='users_mgmt'),
    path('user-management/add-user/<int:action_user>', views.add_user, name='add_user'),
    path('download-audit-trail-pdf/', views.download_audit_trail_pdf, name='download_audit_trail_pdf'),
    path('download-admin-audit-pdf/', views.download_admin_audit_pdf, name='download_admin_audit_pdf'),

]