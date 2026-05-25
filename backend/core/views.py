from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from .models import Tenant, TenantUser
from .serializers import TenantSerializer, TenantUserSerializer


class TenantViewSet(viewsets.ModelViewSet):
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer


@api_view(['GET'])
def current_tenant(request):
    tenant = getattr(request, 'tenant', None)
    if tenant:
        return Response(TenantSerializer(tenant).data)
    return Response({'detail': 'No tenant found'}, status=404)
