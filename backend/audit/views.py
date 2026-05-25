from rest_framework import viewsets
from .models import AuditTrail
from .serializers import AuditTrailSerializer


class AuditTrailViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditTrail.objects.all()
    serializer_class = AuditTrailSerializer

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            return AuditTrail.objects.filter(tenant=tenant)
        return AuditTrail.objects.all()
