from django.urls import path
from checklist import views
from django.contrib.auth import views as auth_views

app_name = 'checklist'

urlpatterns = [
    path('login/', views.login_view, name='login_view'),
    #path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),  
    path('checklist-upload/<int:user_id>', views.checklist_editor, name= 'checklist_editor'),
    path('checklist-review/<int:checklist_id>', views.checklist_reviewer, name= 'checklist_reviewer'),

]