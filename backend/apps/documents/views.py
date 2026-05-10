"""
Documents views: Document CRUD, OCR processing, audit logs
"""
import logging
import random
from datetime import date

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from .models import Document, DocumentAuditLog
from .serializers import (
    DocumentSerializer, DocumentDetailSerializer,
    DocumentAuditLogSerializer, DocumentUploadSerializer,
    OCRProcessSerializer,
)

logger = logging.getLogger(__name__)


def get_client_ip(request) -> str:
    """Extract client IP from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


class DocumentViewSet(ModelViewSet):
    """
    Full CRUD for documents with OCR and archiving support.

    GET    /documents/                   - list
    POST   /documents/                   - upload
    GET    /documents/{id}/              - retrieve
    PUT    /documents/{id}/              - update
    PATCH  /documents/{id}/              - partial update
    DELETE /documents/{id}/              - delete
    POST   /documents/{id}/ocr/          - trigger OCR
    POST   /documents/{id}/archive/      - archive
    POST   /documents/{id}/restore/      - restore from archive
    GET    /documents/{id}/audit/        - audit logs
    GET    /documents/search/?q=text     - full-text search in OCR
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        'file_type', 'document_category', 'is_archived', 'uploaded_by',
    ]
    search_fields = ['title', 'description', 'unique_id', 'ocr_text']
    ordering_fields = ['uploaded_at', 'title', 'file_size', 'retention_until']
    ordering = ['-uploaded_at']

    def get_queryset(self):
        qs = Document.objects.select_related('uploaded_by')
        # Filter archived by default
        show_archived = self.request.query_params.get('include_archived', 'false').lower()
        if show_archived != 'true' and self.action == 'list':
            qs = qs.filter(is_archived=False)
        return qs

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return DocumentDetailSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return DocumentUploadSerializer
        return DocumentSerializer

    def perform_create(self, serializer):
        doc = serializer.save(uploaded_by=self.request.user)
        DocumentAuditLog.objects.create(
            document=doc,
            action=DocumentAuditLog.Action.UPLOADED,
            performed_by=self.request.user,
            ip_address=get_client_ip(self.request),
            details={
                'title': doc.title,
                'file_type': doc.file_type,
                'file_size': doc.file_size,
                'document_category': doc.document_category,
            },
        )
        logger.info(f"Document uploaded: {doc.unique_id} by {self.request.user.email}")

    def perform_update(self, serializer):
        old = self.get_object()
        doc = serializer.save()
        DocumentAuditLog.objects.create(
            document=doc,
            action=DocumentAuditLog.Action.UPDATED,
            performed_by=self.request.user,
            ip_address=get_client_ip(self.request),
            details={'updated_fields': list(serializer.validated_data.keys())},
        )

    def perform_destroy(self, instance):
        DocumentAuditLog.objects.create(
            document=instance,
            action=DocumentAuditLog.Action.DELETED,
            performed_by=self.request.user,
            ip_address=get_client_ip(self.request),
            details={'title': instance.title, 'unique_id': instance.unique_id},
        )
        instance.delete()

    @action(detail=True, methods=['post'], url_path='ocr')
    def ocr(self, request, pk=None):
        """Trigger OCR processing for this document (mock implementation)."""
        from django.utils import timezone

        doc = self.get_object()

        if doc.file_type not in [
            Document.FileType.PDF, Document.FileType.JPG,
            Document.FileType.PNG, Document.FileType.HEIC, Document.FileType.TIFF,
        ]:
            return Response(
                {'error': f'OCR not supported for file type {doc.file_type}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Mock OCR - in production call AWS Textract / Google Vision
        mock_texts = {
            Document.DocumentCategory.INVOICE: (
                f"RECHNUNG\n"
                f"Von: Musterfirma AG, Zürich\n"
                f"An: Property Management GmbH\n"
                f"Datum: {date.today().strftime('%d.%m.%Y')}\n"
                f"Betrag: CHF 1'234.00\n"
                f"MwSt 8.1%: CHF 100.00\n"
                f"IBAN: CH56 0483 5012 3456 7800 9\n"
                f"Referenz: RF18 5390 0754 7034\n"
            ),
            Document.DocumentCategory.CONTRACT: (
                f"VERWALTUNGSVERTRAG\n"
                f"Zwischen den Parteien wird folgender Vertrag vereinbart...\n"
                f"Verwaltungsgebühr: CHF 2'400.00 jährlich\n"
                f"Laufzeit: {date.today().year} bis unbegrenzt\n"
            ),
            Document.DocumentCategory.BANK_STATEMENT: (
                f"KONTOAUSZUG\n"
                f"Konto: CH12 3456 7890 1234 5678 9\n"
                f"Periode: {date.today().strftime('%m.%Y')}\n"
                f"Saldo: CHF 45'678.90\n"
            ),
        }

        ocr_text = mock_texts.get(
            doc.document_category,
            f"Dokument: {doc.title}\nDatum: {date.today()}\nKategorie: {doc.document_category}"
        )
        confidence = round(random.uniform(0.75, 0.97), 4)

        doc.ocr_text = ocr_text
        doc.ocr_confidence = confidence
        doc.ocr_processed_at = timezone.now()
        doc.save(update_fields=['ocr_text', 'ocr_confidence', 'ocr_processed_at', 'updated_at'])

        DocumentAuditLog.objects.create(
            document=doc,
            action=DocumentAuditLog.Action.OCR_PROCESSED,
            performed_by=request.user,
            ip_address=get_client_ip(request),
            details={'confidence': confidence, 'provider': 'mock'},
        )

        return Response({
            'document_id': doc.id,
            'unique_id': doc.unique_id,
            'ocr_text': ocr_text,
            'confidence': confidence,
            'processed_at': doc.ocr_processed_at,
        })

    @action(detail=True, methods=['post'], url_path='archive')
    def archive(self, request, pk=None):
        """Archive this document."""
        doc = self.get_object()
        if doc.is_archived:
            return Response({'error': 'Document is already archived.'}, status=status.HTTP_400_BAD_REQUEST)
        doc.is_archived = True
        doc.save(update_fields=['is_archived', 'updated_at'])
        DocumentAuditLog.objects.create(
            document=doc,
            action=DocumentAuditLog.Action.ARCHIVED,
            performed_by=request.user,
            ip_address=get_client_ip(request),
        )
        return Response({'message': f'Document {doc.unique_id} archived.'})

    @action(detail=True, methods=['post'], url_path='restore')
    def restore(self, request, pk=None):
        """Restore a document from archive."""
        doc = self.get_object()
        if not doc.is_archived:
            return Response({'error': 'Document is not archived.'}, status=status.HTTP_400_BAD_REQUEST)
        doc.is_archived = False
        doc.save(update_fields=['is_archived', 'updated_at'])
        DocumentAuditLog.objects.create(
            document=doc,
            action=DocumentAuditLog.Action.RESTORED,
            performed_by=request.user,
            ip_address=get_client_ip(request),
        )
        return Response({'message': f'Document {doc.unique_id} restored.'})

    @action(detail=True, methods=['get'], url_path='audit')
    def audit(self, request, pk=None):
        """Get audit logs for this document."""
        doc = self.get_object()
        logs = doc.audit_logs.select_related('performed_by').order_by('-timestamp')
        serializer = DocumentAuditLogSerializer(logs, many=True, context={'request': request})
        return Response({
            'document_id': doc.id,
            'unique_id': doc.unique_id,
            'audit_logs': serializer.data,
        })

    @action(detail=False, methods=['get'], url_path='search')
    def search(self, request):
        """Full-text search across document titles, descriptions, and OCR text."""
        query = request.query_params.get('q', '').strip()
        if not query or len(query) < 2:
            return Response(
                {'error': 'Provide at least 2 characters in the search query (q parameter).'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from django.db.models import Q
        qs = Document.objects.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(ocr_text__icontains=query)
        ).filter(is_archived=False).select_related('uploaded_by')

        serializer = DocumentSerializer(qs[:50], many=True, context={'request': request})
        return Response({
            'query': query,
            'count': qs.count(),
            'results': serializer.data,
        })

    def retrieve(self, request, *args, **kwargs):
        """Log document access in audit trail."""
        instance = self.get_object()
        DocumentAuditLog.objects.create(
            document=instance,
            action=DocumentAuditLog.Action.VIEWED,
            performed_by=request.user,
            ip_address=get_client_ip(request),
        )
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class DocumentAuditLogView(generics.ListAPIView):
    """
    List all document audit logs.
    GET /documents/audit/
    """
    serializer_class = DocumentAuditLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['document', 'action', 'performed_by']
    ordering = ['-timestamp']

    def get_queryset(self):
        return DocumentAuditLog.objects.select_related(
            'document', 'performed_by'
        ).all()
