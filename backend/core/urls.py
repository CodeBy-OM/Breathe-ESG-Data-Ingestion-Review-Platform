from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('tenants', views.TenantViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('current-tenant/', views.current_tenant),
]
