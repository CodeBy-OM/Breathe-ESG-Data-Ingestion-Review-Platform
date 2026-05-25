from rest_framework import serializers
from .models import AuditTrail


class AuditTrailSerializer(serializers.ModelSerializer):
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    class Meta:
        model = AuditTrail
        fields = '__all__'
