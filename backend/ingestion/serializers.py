from rest_framework import serializers
from .models import DataImport, NormalizedRecord


class DataImportSerializer(serializers.ModelSerializer):
    source_display = serializers.CharField(source='get_source_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = DataImport
        fields = [
            'id', 'tenant', 'source', 'source_display', 'filename', 'status', 'status_display',
            'uploaded_at', 'processed_at', 'total_rows', 'successful_rows',
            'failed_rows', 'suspicious_rows', 'error_log',
        ]
        read_only_fields = ['uploaded_at', 'processed_at', 'total_rows',
                           'successful_rows', 'failed_rows', 'suspicious_rows']


class NormalizedRecordSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    review_status_display = serializers.CharField(source='get_review_status_display', read_only=True)

    class Meta:
        model = NormalizedRecord
        fields = [
            'id', 'import_job', 'category', 'category_display', 'subcategory',
            'activity_date', 'period_start', 'period_end',
            'quantity', 'unit', 'co2e_kg',
            'location', 'supplier', 'cost_gbp', 'currency_original', 'cost_original',
            'normalization_notes',
            'quality_score', 'quality_issues', 'is_suspicious', 'is_duplicate',
            'review_status', 'review_status_display', 'reviewed_at', 'review_notes',
            'is_locked', 'created_at',
        ]
        read_only_fields = ['created_at', 'co2e_kg']


class NormalizedRecordDetailSerializer(NormalizedRecordSerializer):
    """Full detail including raw_data for single record view"""
    class Meta(NormalizedRecordSerializer.Meta):
        fields = NormalizedRecordSerializer.Meta.fields + ['raw_data', 'reviewed_by']
