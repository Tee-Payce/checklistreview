import json
from django.shortcuts import render
import urllib.request
from django.shortcuts import render, redirect, get_object_or_404
from django.core.mail import send_mail
from .models import Checklist, Comment, Users
from .forms import ChecklistForm, CommentForm
from django.contrib import messages
from django.contrib.auth import login, authenticate

def checklist_editor(request, user_id):
    user = Users.objects.get(id= user_id)
    
    if request.method == 'POST':
        form = ChecklistForm(request.POST, request.FILES)
        if form.is_valid():
            checklist = form.save(commit=False)
            checklist.uploaded_by = user
            checklist.save()
            # Send email to the reviewer
            reviewer = checklist.reviewer
            subject = f'New Checklist Uploaded - {checklist.checklist_type}'
            message = f'A new checklist has been uploaded for your review. Please click the following link to access it: http://10.170.4.222:8081/checklist-reviewer/{checklist.id}'
            send_mail(subject, message, 'InformationSecurity@fbc.co.zw', [reviewer.user_email])
            messages.success(request, f'CHecklist Successfully sent to {reviewer.user_email}')
            return redirect('checklist:checklist_editor', user_id=user.id)
        else:
            messages.error(request, 'Message not sent!!')
            return redirect('checklist:checklist_editor', user_id=user.id)
    else:
        form = ChecklistForm()
    return render(request, 'checklist/uploader.html', {'form': form, 'user':user})


def checklist_reviewer(request, checklist_id):
    
    checklist = get_object_or_404(Checklist, pk=checklist_id)
    if request.method == 'POST':
        form = CommentForm(request.POST, request.FILES)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.checklist = checklist
            comment.reviewer = request.user
            comment.save()
            # Send email to the editor with the signed document
            editor = checklist.uploaded_by
            subject = f'Checklist Reviewed - {checklist.checklist_type}'
            message = f'The checklist you uploaded has been reviewed and signed. You can access the reviewed document at: http://10.170.4.222:8081/checklist-editor/{checklist.id}/'
            send_mail(subject, message, 'informationSecurity@fbc.co.zw', [editor.user_email])
            messages.success(request, f'Checklist and comment have been sent successfully to {editor.user_email}')
            return redirect('checklist:checklist_reviewer', checklist_id=checklist_id)
        else:
            messages.error(request, 'failed to send Checklist!')   
            return redirect('checklist:checklist_reviewer', checklist_id=checklist_id)
    else:
        form = CommentForm()
    return render(request, 'checklist/reviewer.html', {'checklist': checklist, 'form': form})


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Prepare the request data
        data = {
            'username': username,
            'password': password
        }
        data_bytes = json.dumps(data).encode('utf-8')

        # Send the POST request to the API
        req = urllib.request.Request('http://10.170.3.52:9092/ad/login', data=data_bytes, method='POST')
        req.add_header('Content-Type', 'application/json')
        try:
            with urllib.request.urlopen(req) as response:
                response_data = json.load(response)

                # Check the response
                if response_data['respCode'] == '00':
                    # Login successful, check the user's role in the database
                    print(f"Login successful for user: {username}")
                    user, created = Users.objects.get_or_create(
                        username=username
                    )

                    # Set the user's role
                    if created:
                        user.role = 'editor'  # Default role
                        user.save()
                        print(f"New user created with role: {user.role}")
                    else:
                        print(f"Existing user found with role: {user.role}")

                    request.session['username']= user.username
                    # Redirect to the appropriate view based on the user's role
                    if user.role == 'editor':
                        print("Redirecting to checklist_editor")
                        return redirect('checklist:checklist_editor', user_id = user.id)
                    elif user.role == 'reviewer':
                        # Get checklist_id from the URL parameters
                        checklist_id = request.GET.get('checklist_id') 
                        if checklist_id:
                            print("Redirecting to checklist_reviewer")
                            return redirect('checklist:checklist_reviewer', checklist_id=checklist_id)
                        else:
                            messages.error(request, 'Invalid checklist ID')
                            print("Invalid checklist ID")

                    else:
                        messages.error(request, 'Invalid user role')
                        print("Invalid user role")
                        
                    
                else:
                    # Login failed, display an error message
                    messages.error(request, response_data['respDesc'])
                    print(f"Login failed: {response_data['respDesc']}")
        except urllib.error.URLError as e:
            messages.error(request, 'Error connecting to the API: ' + str(e))
            print(f"Error connecting to API: {e}")

    return render(request, 'checklist/login.html')