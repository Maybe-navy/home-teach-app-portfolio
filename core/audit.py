from personal_info.models import AccessLog
from django.utils.deprecation import MiddlewareMixin

SENSITIVE_PREFIXES = ["/portal/teacher/students/", "/portal/admin/assignments"]


class AuditLogMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        path = getattr(request, "path", "")
        if any(path.startswith(p) for p in SENSITIVE_PREFIXES):
            student_id = None
            teacher_id = None
            if getattr(request, "resolver_match", None):
                student_id = request.resolver_match.kwargs.get("student_id")
                teacher_id = request.resolver_match.kwargs.get("teacher_id")
            AccessLog.objects.create(
                user=request.user if getattr(request, "user", None) and request.user.is_authenticated else None,
                path=path,
                method=getattr(request, "method", ""),
                student_id=student_id,
                teacher_id=teacher_id,
                status_code=getattr(response, "status_code", 0),
            )
        return response
