from .models import Tenant
import threading

_thread_locals = threading.local()

def get_current_tenant():
    return getattr(_thread_locals, 'tenant', None)

class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Resolve tenant from header or default to first
        tenant_slug = request.headers.get('X-Tenant-Slug', None)
        if tenant_slug:
            try:
                _thread_locals.tenant = Tenant.objects.get(slug=tenant_slug, is_active=True)
            except Tenant.DoesNotExist:
                _thread_locals.tenant = None
        else:
            _thread_locals.tenant = Tenant.objects.filter(is_active=True).first()

        request.tenant = _thread_locals.tenant
        response = self.get_response(request)
        return response
