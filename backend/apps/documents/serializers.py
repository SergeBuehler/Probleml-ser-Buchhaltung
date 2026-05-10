"""
Documents serializers: Document, DocumentAuditLog
"""
from rest_framework import serializers
from apps.accounts.serializers import UserSerializer
from .models import Document, DocumentAuditLog


class DocumentAuditLogSerializer(serializers.ModelSerializer):
    """Serializer for DocumentAuditLog."""
    performed_by_detail = UserSerializer(source='performed_by', read_only=True)

    class Meta:
        model = DocumentAuditLog
        fields = [
            'id', 'document', 'action', 'performed_by', 'performed_by_detail',
            'timestamp', 'details', 'ip_address',
        ]
        read_only_fields = ['id', 'timestamp']


class DocumentSerializer(serializers.ModelSerializer):
    """Serializer for Document model."""
    uploaded_by_detail = UserSerializer(source='uploaded_by', read_only=True)
    file_url = serializers.SerializerMethodField()
    file_size_human = serializers.ReadOnlyField()
    is_retention_expired = serializers.ReadOnlyField()
    days_until_retention = serializers.ReadOnlyField()

    class Meta:
        model = Document
        fields = [
            'id', 'unique_id', 'title', 'description',
            'file', 'file_url', 'file_type', 'file_size', 'file_size_human',
            'document_category', 'uploaded_by', 'uploaded_by_detail', 'uploaded_at',
            'is_archived', 'retention_until', 'is_retention_expired', 'days_until_retention',
            'ocr_text', 'ocr_processed_at', 'ocr_confidence',
            'metadata', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'unique_id', 'uploaded_at', 'uploaded_by',
            'ocr_processed_at', 'ocr_confidence', 'created_at', 'updated_at',
        ]
        extra_kwargs = {
            'file': {'write_only': False},
        }

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            try:
                return request.build_absolute_uri(obj.file.url)
            except Exception:
                return None
        return None

    def create(self, validated_data):
        # Auto-calculate file size on upload
        file = validated_data.get('file')
        if file:
            validated_data['file_size'] = file.size
        return super().create(validated_data)


class DocumentDetailSerializer(DocumentSerializer):
    """Detailed serializer including audit logs."""
    audit_logs = DocumentAuditLogSerializer(many=True, read_only=True)

    class Meta(DocumentSerializer.Meta):
        fields = DocumentSerializer.Meta.fields + ['audit_logs']


class DocumentUploadSerializer(serializers.ModelSerializer):
    """Simplified serializer for document uploads."""

    class Meta:
        model = Document
        fields = [
            'title', 'description', 'file', 'document_category',
            'file_type', 'retention_until', 'metadata',
        ]

    def create(self, validated_data):
        file = validated_data.get('file')
        if file:
            validated_data['file_size'] = file.size
        return super().create(validated_data)


class OCRProcessSerializer(serializers.Serializer):
    """Serializer for OCR processing response."""
    document_id = serializers.IntegerField()
    unique_id = serializers.CharField()
    ocr_text = serializers.CharField(allow_blank=True)
    confidence = serializers.FloatField()
    processed_at = serializers.DateTimeField()
