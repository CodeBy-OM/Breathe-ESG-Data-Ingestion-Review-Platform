from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('imports', views.DataImportViewSet)
router.register('records', views.NormalizedRecordViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/stats/', views.dashboard_stats),
    path('generate-sample/', views.generate_sample_data),
]
