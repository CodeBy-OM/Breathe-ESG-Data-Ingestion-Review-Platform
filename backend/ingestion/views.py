import json
from datetime import datetime
from django.utils import timezone
from rest_framework import viewsets, status, filters
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django_filters.rest_framework import DjangoFilterBackend

from .models import DataImport, NormalizedRecord
from .serializers import DataImportSerializer, NormalizedRecordSerializer, NormalizedRecordDetailSerializer
from .normalizers import SAPNormalizer, UtilityNormalizer, TravelNormalizer


NORMALIZERS = {
    'sap': SAPNormalizer,
    'utility': UtilityNormalizer,
    'travel': TravelNormalizer,
}


class DataImportViewSet(viewsets.ModelViewSet):
    queryset = DataImport.objects.all()
    serializer_class = DataImportSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['source', 'status']
    ordering = ['-uploaded_at']

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            return DataImport.objects.filter(tenant=tenant)
        return DataImport.objects.all()

    def create(self, request, *args, **kwargs):
        source = request.data.get('source')
        if source not in NORMALIZERS:
            return Response({'error': f"Invalid source. Choose from: {list(NORMALIZERS.keys())}"}, status=400)
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response({'error': 'No file provided'}, status=400)
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            from core.models import Tenant
            tenant, _ = Tenant.objects.get_or_create(slug='default', defaults={'name': 'Default Company'})
        import_job = DataImport.objects.create(
            tenant=tenant, source=source, filename=uploaded_file.name,
            file_path=uploaded_file, status='processing',
            uploaded_by=request.user if request.user.is_authenticated else None,
        )
        try:
            file_content = uploaded_file.read()
            result = NORMALIZERS[source]().normalize(file_content, uploaded_file.name)
            records_created = 0; failed = 0; suspicious = 0
            for rec in result['records']:
                try:
                    NormalizedRecord.objects.create(
                        tenant=tenant, import_job=import_job, category=rec['category'],
                        subcategory=rec.get('subcategory',''), activity_date=rec['activity_date'] or datetime.now().date(),
                        period_start=rec.get('period_start'), period_end=rec.get('period_end'),
                        quantity=rec['quantity'], unit=rec['unit'], co2e_kg=rec.get('co2e_kg',0),
                        location=rec.get('location',''), supplier=rec.get('supplier',''),
                        cost_gbp=rec.get('cost_gbp'), currency_original=rec.get('currency_original',''),
                        cost_original=rec.get('cost_original'), raw_data=rec.get('raw_data',{}),
                        normalization_notes=rec.get('normalization_notes',''),
                        quality_score=rec.get('quality_score',1.0), quality_issues=rec.get('quality_issues',[]),
                        is_suspicious=rec.get('is_suspicious',False),
                        review_status='flagged' if rec.get('is_suspicious') else 'pending',
                    )
                    records_created += 1
                    if rec.get('is_suspicious'): suspicious += 1
                except Exception: failed += 1
            import_job.status='completed'; import_job.processed_at=timezone.now()
            import_job.total_rows=len(result['records']); import_job.successful_rows=records_created
            import_job.failed_rows=failed; import_job.suspicious_rows=suspicious
            import_job.error_log=json.dumps(result.get('errors',[])); import_job.save()
            return Response(DataImportSerializer(import_job).data, status=201)
        except Exception as e:
            import_job.status='failed'; import_job.error_log=str(e); import_job.save()
            return Response({'error': str(e)}, status=500)

    @action(detail=True, methods=['get'])
    def records(self, request, pk=None):
        import_job = self.get_object()
        records = NormalizedRecord.objects.filter(import_job=import_job)
        return Response(NormalizedRecordSerializer(records, many=True).data)


class NormalizedRecordViewSet(viewsets.ModelViewSet):
    queryset = NormalizedRecord.objects.all()
    serializer_class = NormalizedRecordSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'review_status', 'is_suspicious', 'import_job', 'is_locked']
    search_fields = ['location', 'supplier', 'subcategory']
    ordering_fields = ['activity_date', 'co2e_kg', 'quantity', 'quality_score']
    ordering = ['-activity_date']

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            return NormalizedRecord.objects.filter(tenant=tenant)
        return NormalizedRecord.objects.all()

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return NormalizedRecordDetailSerializer
        return NormalizedRecordSerializer

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        r = self.get_object()
        if r.is_locked: return Response({'error': 'Record is locked'}, status=400)
        r.review_status='approved'; r.reviewed_by=request.user if request.user.is_authenticated else None
        r.reviewed_at=timezone.now(); r.review_notes=request.data.get('notes',''); r.save()
        return Response(NormalizedRecordSerializer(r).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        r = self.get_object()
        if r.is_locked: return Response({'error': 'Record is locked'}, status=400)
        r.review_status='rejected'; r.reviewed_by=request.user if request.user.is_authenticated else None
        r.reviewed_at=timezone.now(); r.review_notes=request.data.get('notes',''); r.save()
        return Response(NormalizedRecordSerializer(r).data)

    @action(detail=True, methods=['post'])
    def flag(self, request, pk=None):
        r = self.get_object()
        r.review_status='flagged'; r.review_notes=request.data.get('notes',''); r.save()
        return Response(NormalizedRecordSerializer(r).data)

    @action(detail=False, methods=['post'])
    def bulk_approve(self, request):
        ids = request.data.get('ids', [])
        count = NormalizedRecord.objects.filter(id__in=ids, is_locked=False).update(
            review_status='approved', reviewed_at=timezone.now())
        return Response({'approved': count})

    @action(detail=False, methods=['post'])
    def lock_approved(self, request):
        tenant = getattr(request, 'tenant', None)
        qs = NormalizedRecord.objects.filter(review_status='approved', is_locked=False)
        if tenant: qs = qs.filter(tenant=tenant)
        count = qs.update(is_locked=True)
        return Response({'locked': count})


@api_view(['GET'])
def dashboard_stats(request):
    tenant = getattr(request, 'tenant', None)
    qs = NormalizedRecord.objects.all()
    if tenant: qs = qs.filter(tenant=tenant)
    from django.db.models import Sum
    co2_by_cat = {}
    for cat, label in NormalizedRecord.CATEGORY_CHOICES:
        total_co2 = qs.filter(category=cat).aggregate(t=Sum('co2e_kg'))['t'] or 0
        co2_by_cat[cat] = round(total_co2 / 1000, 2)
    total_co2 = qs.aggregate(t=Sum('co2e_kg'))['t'] or 0
    recent_imports = DataImport.objects.all()
    if tenant: recent_imports = recent_imports.filter(tenant=tenant)
    return Response({
        'records': {
            'total': qs.count(), 'pending': qs.filter(review_status='pending').count(),
            'approved': qs.filter(review_status='approved').count(),
            'rejected': qs.filter(review_status='rejected').count(),
            'flagged': qs.filter(review_status='flagged').count(),
            'suspicious': qs.filter(is_suspicious=True).count(),
            'locked': qs.filter(is_locked=True).count(),
        },
        'emissions': {'total_tco2e': round(total_co2/1000,2), 'by_category': co2_by_cat},
        'recent_imports': DataImportSerializer(recent_imports[:5], many=True).data,
    })


@api_view(['POST'])
def generate_sample_data(request):
    source = request.data.get('source', 'sap')
    from .sample_data import get_sample_csv
    csv_content = get_sample_csv(source)
    tenant = getattr(request, 'tenant', None)
    if not tenant:
        from core.models import Tenant
        tenant, _ = Tenant.objects.get_or_create(slug='default', defaults={'name': 'Default Company'})
    normalizer_class = NORMALIZERS.get(source)
    if not normalizer_class: return Response({'error': 'Invalid source'}, status=400)
    result = normalizer_class().normalize(csv_content.encode(), f'sample_{source}.csv')
    import_job = DataImport.objects.create(tenant=tenant, source=source, filename=f'sample_{source}_data.csv', status='processing')
    records_created = 0; suspicious = 0
    for rec in result['records']:
        try:
            NormalizedRecord.objects.create(
                tenant=tenant, import_job=import_job, category=rec['category'],
                subcategory=rec.get('subcategory',''), activity_date=rec['activity_date'] or datetime.now().date(),
                period_start=rec.get('period_start'), period_end=rec.get('period_end'),
                quantity=rec['quantity'], unit=rec['unit'], co2e_kg=rec.get('co2e_kg',0),
                location=rec.get('location',''), supplier=rec.get('supplier',''),
                cost_gbp=rec.get('cost_gbp'), currency_original=rec.get('currency_original',''),
                cost_original=rec.get('cost_original'), raw_data=rec.get('raw_data',{}),
                normalization_notes=rec.get('normalization_notes',''),
                quality_score=rec.get('quality_score',1.0), quality_issues=rec.get('quality_issues',[]),
                is_suspicious=rec.get('is_suspicious',False),
                review_status='flagged' if rec.get('is_suspicious') else 'pending',
            )
            records_created += 1
            if rec.get('is_suspicious'): suspicious += 1
        except Exception: pass
    import_job.status='completed'; import_job.processed_at=timezone.now()
    import_job.total_rows=len(result['records']); import_job.successful_rows=records_created
    import_job.suspicious_rows=suspicious; import_job.save()
    return Response({'message': f'Generated {records_created} sample {source} records', 'import_id': import_job.id, 'suspicious': suspicious})
