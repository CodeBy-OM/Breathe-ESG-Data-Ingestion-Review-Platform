from django.db import models
from django.contrib.auth.models import User


class Tenant(models.Model):
    """Multi-tenancy: each company is a tenant"""
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    country = models.CharField(max_length=100, default='GB')
    reporting_year = models.IntegerField(default=2024)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class TenantUser(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('analyst', 'ESG Analyst'),
        ('auditor', 'Auditor'),
        ('viewer', 'Viewer'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='analyst')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'tenant')

    def __str__(self):
        return f"{self.user.username} @ {self.tenant.name} ({self.role})"
