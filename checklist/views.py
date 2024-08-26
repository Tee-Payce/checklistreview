from email.message import EmailMessage
import json
from django.shortcuts import render
import urllib.request
from django.shortcuts import render, redirect, get_object_or_404
from django.core.mail import send_mail
from .models import AuditLog, Checklist, Comment, Users
from .forms import ChecklistForm, CommentForm, UsersForm
import base64 
from django.core.files.base import ContentFile
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from .middleware import AuditLogMiddleware


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



from django.core.mail import EmailMessage


def checklist_reviewer(request, checklist_id):
    
    checklist = get_object_or_404(Checklist, pk=checklist_id)
    if request.method == 'POST':
        form = CommentForm(request.POST, request.FILES)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.checklist = checklist
            comment.signed_file = request.FILES.get('signed_file')  # Get the uploaded file
            comment.reviewer = checklist.reviewer
            comment.save()
           

            
        
            # Send email to the editor with the signed document
            editor = checklist.uploaded_by
            subject = f'Checklist Reviewed - {checklist.checklist_type}'
            message = f'The checklist you uploaded has been reviewed and signed. With comment: {comment.comment} \n\n '
            
            # Attach the signed file to the email using EmailMessage
            try:
                email = EmailMessage(
                    subject=subject,  # Subject is set here
                    body=message,
                    from_email='informationSecurity@fbc.co.zw',
                    to=[editor.user_email],
                )
                email.attach('signed_checklist.pdf', comment.signed_file.read(), 'application/pdf')
                email.send()
                messages.success(request, f'Checklist and comment have been sent successfully to {editor.user_email}')
            except Exception as e:
                messages.error(request, f'Failed to send checklist: {e}')

            return redirect('checklist:checklist_reviewer', checklist_id=checklist_id)
        else:
            messages.error(request, 'failed to send Checklist!')   
            return redirect('checklist:checklist_reviewer', checklist_id=checklist_id)
    else:
        form = CommentForm()
    return render(request, 'checklist/reviewer.html', {'checklist': checklist, 'form': form})

#9cfd0a27-e37d-41af-966d-9180e5fa2de7 int key
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        audit_trail_access = request.POST.get('audit_trail_access')

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
                    request.audit_log_user = user
                    # Redirect to the appropriate view based on the user's role
                    if user.is_active == True:
                        if audit_trail_access:
                        
                            print("Redirecting to audit_trail")
                            return redirect('checklist:audit_trail', action_user= user.id)
                        elif user.role == 'editor':
                            print("Redirecting to checklist_editor")
                            return redirect('checklist:checklist_editor', user_id=user.id)
                        elif user.role == 'reviewer':
                            # Get checklist_id from the URL parameters
                            checklist = Checklist.objects.filter(reviewer_id=user).last()
                            if checklist:
                                print("Redirecting to checklist_reviewer")
                                return redirect('checklist:checklist_reviewer', checklist_id=checklist.id)
                            else:
                                messages.error(request, 'No checklist has been uploaded for your review')
                                print("Invalid checklist ID")

                        else:
                            messages.error(request, 'Invalid user role')
                            print("Invalid user role")
                    else:
                        messages.error(request, 'User Disabled!!')
                        print("User disabled!!")

                else:
                    # Login failed, display an error message
                    messages.error(request, response_data['respDesc'])
                    print(f"Login failed: {response_data['respDesc']}")
        except urllib.error.URLError as e:
            messages.error(request, 'Error connecting to the API: ' + str(e))
            print(f"Error connecting to API: {e}")

    return render(request, 'checklist/login.html')


from django.http import FileResponse, HttpResponse

from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta, date
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from django.db.models import Max


def audit_trail(request, action_user):
    """View to display and filter audit trail data."""
    users = Users.objects.all()
    user = Users.objects.get(id= action_user)
    
    # Get current date and time
    now = timezone.now()

    start_date = date(2024, 1, 1)  # Earliest possible date
    end_date = date.today()        # Current date

    # Handle filter by week
    if request.GET.get('filter_by') == 'week':
        # Calculate start and end date of the current week
        start_date = now - timedelta(days=now.weekday())
        end_date = start_date + timedelta(days=7)
    elif request.GET.get('filter_by') == 'month':
        # Calculate start and end date of the current month
        start_date = datetime(now.year, now.month, 1)
        end_date = datetime(now.year, now.month, 1) + timedelta(days=32) - timedelta(days=start_date.day)

    
    # Get filter parameters from the request
    # Get filter parameters from the request
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    checklist_type = request.GET.get('checklist_type')
    reviewer_username = request.GET.get('reviewer')  # Use 'reviewer_username'
    editor_username = request.GET.get('editor')  # Use 'editor_username'

    # Convert date strings to datetime objects (if provided)
    if start_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    if end_date_str:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

    # Filter checklists based on selected date range
    checklists = Checklist.objects.filter(
        Q(created_at__date__gte=start_date, created_at__date__lte=end_date) |
        Q(updated_at__date__gte=start_date, updated_at__date__lte=end_date)
    )

    # Handle filter by checklist type
    if checklist_type:
        checklists = checklists.filter(checklist_type=checklist_type)

    # Handle filter by reviewer
    if reviewer_username:
        checklists = checklists.filter(reviewer__username=reviewer_username)  # Use 'reviewer__username'

    # Handle filter by editor
    if editor_username:
        checklists = checklists.filter(uploaded_by__username=editor_username)  # Use 'uploaded_by__username'

    # Fetch comments associated with the filtered checklists
    comments = Comment.objects.filter(checklist__in=checklists)
    if request.GET.get('clear_filters') == 'true':
    # Reset filter parameters
        start_date = date(2024, 1, 1)
        end_date = date.today()
        checklist_type = None
        reviewer_username = None
        editor_username = None

    # Combine checklist and comment data
    audit_trail_data = []
    for checklist in checklists:
        audit_trail_data.append({
            'event': 'Checklist Uploaded for review',
            'user': checklist.uploaded_by.username,
            'date_time': checklist.created_at,
            'details': f'Checklist Type: {checklist.get_checklist_type_display()}',
        })
        audit_trail_data.append({
            'event': 'Checklist Reviewed',
            'user': checklist.reviewer.username,
            'date_time': checklist.updated_at,
            'details': f'Reviewer: {checklist.reviewer.username}',
        })
        for comment in checklist.comments.all():
            audit_trail_data.append({
                'event': 'Comment Added by reviewer',
                'user': comment.reviewer.username,
                'date_time': comment.created_at,
                'details': comment.comment,
            })

    # Sort the audit trail data by date and time
    audit_trail_data.sort(key=lambda item: item['date_time'], reverse=True)

    # Render the template with audit trail data and filter options
    return render(request, 'checklist/audit_trail.html', {
        'audit_trail_data': audit_trail_data,
        'now': now,
        'start_date': start_date,  # Pass start date for the template
        'end_date': end_date,  
        'checklist_types': Checklist.CHECKLIST_TYPES,  
        # Pass checklist types for filtering
        'user': user,
        'users':users,
        'reviewers': users.filter(role='reviewer'),  # Get reviewers
        'editors': users.filter(role='editor'),  # Get editors
        'reviewer_username': reviewer_username,  # Pass reviewer username to template
        'editor_username': editor_username,  # Pass editor username to template
    })
   

@csrf_exempt
def download_audit_trail_pdf(request):
    """View to generate and download a PDF report of the audit trail."""

    """View to generate and download a PDF report of the audit trail."""

    # Get filter parameters from the request
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    checklist_type = request.GET.get('checklist_type')
    reviewer_username = request.GET.get('reviewer')  # Use 'reviewer_username'
    editor_username = request.GET.get('editor')  # Use 'editor_username'

    # Convert date strings to datetime objects
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else date(2024, 1, 1)
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else date.today()

    # Filter checklists based on selected date range
    checklists = Checklist.objects.filter(
        Q(created_at__date__gte=start_date, created_at__date__lte=end_date) |
        Q(updated_at__date__gte=start_date, updated_at__date__lte=end_date)
    )

    # Filter checklists based on checklist type
    if checklist_type:
        checklists = checklists.filter(checklist_type=checklist_type)

    # Filter checklists based on reviewer
    if reviewer_username:
        checklists = checklists.filter(reviewer__username=reviewer_username)  # Use 'reviewer__username'

    # Filter checklists based on editor
    if editor_username:
        checklists = checklists.filter(uploaded_by__username=editor_username)  # Use 'uploaded_by__username'

    # Fetch comments associated with the filtered checklists
    comments = Comment.objects.filter(checklist__in=checklists)

    # Combine checklist and comment data
    audit_trail_data = []
    for checklist in checklists:
        audit_trail_data.append({
            'event': 'Checklist Uploaded for review',
            'user': checklist.uploaded_by.username,
            'date_time': checklist.created_at,
            'details': f'Checklist Type: {checklist.get_checklist_type_display()}',
        })
        audit_trail_data.append({
            'event': 'Checklist Reviewed',
            'user': checklist.reviewer.username,
            'date_time': checklist.updated_at,
            'details': f'Reviewer: {checklist.reviewer.username}',
        })
        for comment in checklist.comments.all():
            audit_trail_data.append({
                'event': 'Comment Added by reviewer',
                'user': comment.reviewer.username,
                'date_time': comment.created_at,
                'details': comment.comment,
            })

    # Sort the audit trail data by date and time
    audit_trail_data.sort(key=lambda item: item['date_time'], reverse=True)

    if not audit_trail_data:
        messages.error(request, 'No audit trail data found.')
        return redirect('checklist:audit_trail')

    

    # Create a buffer to store the PDF content
    buffer = io.BytesIO()

    # Create a PDF canvas
    pdf = canvas.Canvas(buffer, pagesize=letter)

    # Set font and title
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(inch, 10.5 * inch, "Audit Trail Report")

    # Set line spacing
    line_height = 0.3 * inch

    # Iterate through audit trail data and add to PDF
    y = 10 * inch
    for entry in audit_trail_data:
        pdf.setFont("Helvetica", 12)
        pdf.drawString(inch, y, f"Event: {entry['event']}")
        pdf.drawString(inch, y - line_height, f"User: {entry['user']}")
        pdf.drawString(inch, y - 2 * line_height, f"Date and Time: {entry['date_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        pdf.drawString(inch, y - 3 * line_height, f"Details: {entry['details']}")
        y -= 4 * line_height

    # Save the PDF
    pdf.save()

    # Set the response headers
    buffer.seek(0)
    response = FileResponse(buffer, content_type='application/pdf', filename='checklist_report.pdf')
    return response


def users_mgmt(request, action_user):
    users = Users.objects.all()
    action_user = Users.objects.get(id=action_user)
    d_user_id = request.POST.get('d_user_id')
    
    # Modal data for adding a user
    

    # Modal data for editing a user
    edit_user_modal = {
        'title': 'Edit User',
        'form': UsersForm(),  # Placeholder, will be filled when editing
        'action': 'edit_user',
        'button_text': 'Save Changes'
    }

    # Modal data for deleting a user
    delete_user_modal = {
        'title': 'Delete User',
        'message': f'Are you sure you want to delete user {d_user_id}?',
        'action': 'delete_user',
        'button_text': 'Delete',
        'd_user_id': None 
    }

    if request.method == 'POST':
        
        if 'edit_user' in request.POST:
            
            user_id = request.POST.get('edit_user')
            try:
                e_user = Users.objects.get(pk=user_id)
                edit_user_modal['form'] = UsersForm(instance=e_user, data=request.POST)
                if edit_user_modal['form'].is_valid():
                    # Save the updated user
                    updated_user = edit_user_modal['form'].save()
                    # Create an audit log entry for the update
                    AuditLog.objects.create(
                        event='update',
                        action_user = action_user,
                        target_user=updated_user,
                        details=f'User {updated_user.username} updated.'
                    )
                    messages.success(request, 'User updated successfully!')
                    return redirect('checklist:users_mgmt', action_user=action_user.id)
                else:
                    messages.error(request, 'Please correct the errors in the form.')
            except Users.DoesNotExist:
                messages.error(request, 'User not found.')
                return render(request, 'checklist/users_mgmt.html', {
                    'users': users,
                    'action_user': action_user,
                    'edit_user_modal': edit_user_modal,
                    'delete_user_modal': delete_user_modal,
                })
        
           
            except Users.DoesNotExist:
                messages.error(request, 'User not found.')
                return render(request, 'checklist/users_mgmt.html', {
                    'users': users,
                 
                    
                    'user_id': user_id,
                    'action_user': action_user,
                    'edit_user_modal': edit_user_modal,
                    'delete_user_modal': delete_user_modal,
                })
    return render(request, 'checklist/users_mgmt.html', {
        'users': users,
        
        'action_user': action_user,
        'edit_user_modal': edit_user_modal,
        'delete_user_modal': delete_user_modal
    })

def add_user(request, action_user):
    user = Users.objects.get(id=action_user)
    if request.method == 'POST':
        form = UsersForm(request.POST)
        if form.is_valid():
            # Get the maximum primary key value from the existing records
            max_pk = Users.objects.aggregate(Max('id'))['id__max']
            
            # Assign the next primary key value
            form.instance.id = max_pk + 1 if max_pk else 1
            
            # Save the new user
            new_user = form.save()
            
            # Create an audit log entry for the addition
            AuditLog.objects.create(
                event='create',
                action_user = user,
                target_user=new_user,
                details=f'User {new_user.username} created.'
            )
            
            messages.success(request, 'User added successfully!')
            return redirect('checklist:users_mgmt', action_user)
        else:
            messages.error(request, 'Please correct the errors in the form.')
    else:
        # If the request is not POST, render the form
        form = UsersForm()  # Create an empty form instance
        return render(request, 'checklist/add_user.html', {'form': form})

    return render(request, 'checklist/add_user.html', {'form': form, 'user': user})

def create_audit_log(event, action_user, target_user, details):
  
    try:
        # Save the target_user object first, if it hasn't been saved yet
        if target_user.pk is None:
            target_user.save()

        audit_log = AuditLog(
            event=event,
            action_user=action_user,
            target_user=target_user,
            details=details
        )
        audit_log.save()
    except Exception as e:
        # Log the error or handle it in another appropriate way
        print(f"Error creating audit log: {e}")

def delete_user(request, user_id, action_user_id):
    try:
        user = Users.objects.get(pk=user_id)
        action_user = Users.objects.get(pk=action_user_id)
  
        
        if request.method == 'POST':
            # Create an audit log entry for the deletion
            create_audit_log(
            event='disable',
            action_user=action_user,
            target_user=user,
            details=f'User {user.username} disabled.'
            )
            user.is_active = False
            user.save()
            # Create an audit log entry
            

            messages.success(request, 'User disabled successfully!')
            return redirect('checklist:users_mgmt', action_user_id)
        return render(request, 'checklist/delete_user.html', {'user': user, 'action_user': action_user})
    except Users.DoesNotExist:
        messages.error(request, 'User not found.')
        
    return redirect('checklist:users_mgmt', action_user_id)
#user audits
def admin_audit(request, action_user):
    """View to display and filter audit trail data for admin actions."""
    users = Users.objects.all()
    user = Users.objects.get(id= action_user)
    # Get current date and time
    now = timezone.now()

    start_date = date(2024, 1, 1)  # Earliest possible date
    end_date = date.today()        # Current date

    # Get filter parameters from the request
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    user_username = request.GET.get('user_username')  # Filter by user

    # Convert date strings to datetime objects (if provided)
    if start_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    if end_date_str:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

    # Filter audit logs based on selected date range
    audit_logs = AuditLog.objects.filter(
        Q(created_at__date__gte=start_date, created_at__date__lte=end_date)
    )

    # Handle filter by user
    if user_username:
        audit_logs = audit_logs.filter(action_user_id__username=user_username)

    # Combine audit log data
    audit_trail_data = []
    for audit_log in audit_logs:
        event_details = {
            'event': audit_log.event,
            'user': audit_log.action_user_id,
            'target_user': audit_log.target_user,
            'date_time': audit_log.created_at,
            'details': audit_log.details,
        }

        

        audit_trail_data.append(event_details)

    # Sort the audit trail data by date and time
    audit_trail_data.sort(key=lambda item: item['date_time'], reverse=True)

    # Render the template with audit trail data and filter options
    return render(request, 'checklist/admin_audit.html', {
        'audit_trail_data': audit_trail_data,
        'now': now,
        'start_date': start_date,  # Pass start date for the template
        'end_date': end_date,
        'users': users,
        'user':user,
        'user_username': user_username,  # Pass user username to template
    })

@csrf_exempt
def download_admin_audit_pdf(request):
    """View to generate and download a PDF report of the admin audit trail."""

    # Get filter parameters from the request
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    user_username = request.GET.get('user_username')  # Filter by user

    # Convert date strings to datetime objects
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else date(2024, 1, 1)
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else date.today()

    # Filter audit logs based on selected date range
    audit_logs = AuditLog.objects.filter(
        Q(created_at__date__gte=start_date, created_at__date__lte=end_date)
    )

    # Handle filter by user
    if user_username:
        audit_logs = audit_logs.filter(action_user__username=user_username)

    # Combine audit log data
    audit_trail_data = []
    for audit_log in audit_logs:
        event_details = {
            'event': audit_log.event,
            'user': audit_log.action_user_id,
            'target_user': audit_log.target_user,
            'date_time': audit_log.created_at,
            'details': audit_log.details,
        }

       
        audit_trail_data.append(event_details)

    # Sort the audit trail data by date and time
    audit_trail_data.sort(key=lambda item: item['date_time'], reverse=True)

    if not audit_trail_data:
        messages.error(request, 'No audit trail data found.')
        return redirect('checklist:admin_audit')

    # Create a buffer to store the PDF content
    buffer = io.BytesIO()

    # Create a PDF canvas
    pdf = canvas.Canvas(buffer, pagesize=letter)

    # Set font and title
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(inch, 10.5 * inch, "Admin Audit Trail Report")

    # Set line spacing
    line_height = 0.3 * inch

    # Iterate through audit trail data and add to PDF
    y = 10 * inch
    for entry in audit_trail_data:
        pdf.setFont("Helvetica", 12)
        pdf.drawString(inch, y, f"Event: {entry['event']}")
        pdf.drawString(inch, y - line_height, f"User: {entry['user']}")
        pdf.drawString(inch, y - 2 * line_height, f"Date and Time: {entry['date_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        pdf.drawString(inch, y - 3 * line_height, f"Details: {entry['details']}")
        y -= 4 * line_height

       

    # Save the PDF
    pdf.save()

    # Set the response headers
    buffer.seek(0)
    response = FileResponse(buffer, content_type='application/pdf', filename='admin_audit_report.pdf')
    return response