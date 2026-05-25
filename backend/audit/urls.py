from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('audit-trail', views.AuditTrailViewSet)

urlpatterns = [path('', include(router.urls))]
