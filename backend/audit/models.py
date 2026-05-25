from django.db import models
from django.contrib.auth.models import User
from core.models import Tenant
from ingestion.models import NormalizedRecord


class AuditTrail(models.Model):
    ACTION_CHOICES = [
        ('created', 'Record Created'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('flagged', 'Flagged'),
        ('edited', 'Edited'),
        ('locked', 'Locked for Audit'),
        ('imported', 'Data Imported'),
    ]
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    record = models.ForeignKey(NormalizedRecord, on_delete=models.CASCADE, null=True, blank=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    before_state = models.JSONField(default=dict)
    after_state = models.JSONField(default=dict)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.action} by {self.performed_by} at {self.timestamp}"
