from django.utils.deprecation import MiddlewareMixin
from .models import AuditLog, Users

class AuditLogMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Retrieve the username from the session
        username = request.session.get('username')
        if username:
            try:
                # Retrieve the user from the database
                request.audit_log_user = Users.objects.get(username=username)
            except Users.DoesNotExist:
                request.audit_log_user = None
        else:
            request.audit_log_user = None
        return None

    def process_response(self, request, response):
        return response