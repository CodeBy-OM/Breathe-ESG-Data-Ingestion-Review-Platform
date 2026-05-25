from django.db import models
from django.contrib.auth.models import User
from core.models import Tenant
import json


class DataImport(models.Model):
    """Tracks each import job"""
    SOURCE_CHOICES = [
        ('sap', 'SAP (Fuel & Procurement)'),
        ('utility', 'Utility / Electricity'),
        ('travel', 'Corporate Travel'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    filename = models.CharField(max_length=500, blank=True)
    file_path = models.FileField(upload_to='imports/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    total_rows = models.IntegerField(default=0)
    successful_rows = models.IntegerField(default=0)
    failed_rows = models.IntegerField(default=0)
    suspicious_rows = models.IntegerField(default=0)

    error_log = models.TextField(blank=True)
    raw_headers = models.TextField(blank=True)  # JSON of original headers

    def __str__(self):
        return f"{self.get_source_display()} import - {self.uploaded_at.date()} ({self.status})"

    class Meta:
        ordering = ['-uploaded_at']


class NormalizedRecord(models.Model):
    """Canonical ESG emission record after normalization"""
    REVIEW_STATUS = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('flagged', 'Flagged for Review'),
    ]
    CATEGORY_CHOICES = [
        ('scope1_fuel', 'Scope 1 - Fuel Combustion'),
        ('scope2_electricity', 'Scope 2 - Electricity'),
        ('scope3_travel', 'Scope 3 - Business Travel'),
        ('scope3_procurement', 'Scope 3 - Procurement'),
    ]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    import_job = models.ForeignKey(DataImport, on_delete=models.CASCADE, related_name='records')

    # Classification
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    subcategory = models.CharField(max_length=100, blank=True)  # e.g. diesel, electricity, flight

    # Normalized fields
    activity_date = models.DateField()
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)

    quantity = models.FloatField()                    # normalized quantity
    unit = models.CharField(max_length=50)            # normalized unit (liters, kWh, km, nights)
    co2e_kg = models.FloatField(default=0.0)          # calculated CO2e in kg

    location = models.CharField(max_length=255, blank=True)
    supplier = models.CharField(max_length=255, blank=True)
    cost_gbp = models.FloatField(null=True, blank=True)
    currency_original = models.CharField(max_length=10, blank=True)
    cost_original = models.FloatField(null=True, blank=True)

    # Source-specific metadata stored as JSON
    raw_data = models.JSONField(default=dict)
    normalization_notes = models.TextField(blank=True)  # what was changed

    # Data quality
    quality_score = models.FloatField(default=1.0)   # 0-1, 1=perfect
    quality_issues = models.JSONField(default=list)   # list of issue strings
    is_suspicious = models.BooleanField(default=False)
    is_duplicate = models.BooleanField(default=False)

    # Review workflow
    review_status = models.CharField(max_length=20, choices=REVIEW_STATUS, default='pending')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='reviewed_records')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)
    is_locked = models.BooleanField(default=False)  # locked after audit approval

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.category} | {self.activity_date} | {self.quantity} {self.unit} | {self.co2e_kg:.2f} kgCO2e"

    class Meta:
        ordering = ['-activity_date']
        indexes = [
            models.Index(fields=['tenant', 'review_status']),
            models.Index(fields=['tenant', 'category']),
            models.Index(fields=['activity_date']),
        ]
