"""
Documents models: Document, DocumentAuditLog
"""
from datetime import date, timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


def default_retention_date():
    """Default retention period: 10 years from today (Swiss legal requirement)."""
    return date.today() + timedelta(days=365 * 10)


class Document(models.Model):
    """Represents an uploaded document with OCR support and retention tracking."""

    class FileType(models.TextChoices):
        PDF = 'PDF', _('PDF Document')
        JPG = 'JPG', _('JPEG Image')
        PNG = 'PNG', _('PNG Image')
        HEIC = 'HEIC', _('HEIC Image (iPhone)')
        TIFF = 'TIFF', _('TIFF Image')
        DOCX = 'DOCX', _('Word Document')
        XLSX = 'XLSX', _('Excel Spreadsheet')
        OTHER = 'OTHER', _('Other')

    class DocumentCategory(models.TextChoices):
        CONTRACT = 'CONTRACT', _('Contract / Agreement')
        INVOICE = 'INVOICE', _('Invoice')
        RECEIPT = 'RECEIPT', _('Receipt / Beleg')
        BANK_STATEMENT = 'BANK_STATEMENT', _('Bank Statement')
        PAYROLL = 'PAYROLL', _('Payroll Document')
        TAX = 'TAX', _('Tax Document')
        INSURANCE = 'INSURANCE', _('Insurance Document')
        CORRESPONDENCE = 'CORRESPONDENCE', _('Correspondence')
        PROPERTY = 'PROPERTY', _('Property Document')
        OTHER = 'OTHER', _('Other')

    unique_id = models.CharField(max_length=30, unique=True, blank=True, db_index=True)
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True, default='')
    file = models.FileField(upload_to='documents/%Y/%m/')
    file_type = models.CharField(
        max_length=10, choices=FileType.choices, default=FileType.OTHER
    )
    file_size = models.PositiveBigIntegerField(
        default=0, help_text='File size in bytes.'
    )
    document_category = models.CharField(
        max_length=20, choices=DocumentCategory.choices, default=DocumentCategory.OTHER
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_documents',
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_archived = models.BooleanField(default=False)
    retention_until = models.DateField(
        default=default_retention_date,
        help_text='Swiss legal retention deadline (10 years default).',
    )

    # OCR
    ocr_text = models.TextField(null=True, blank=True)
    ocr_processed_at = models.DateTimeField(null=True, blank=True)
    ocr_confidence = models.FloatField(null=True, blank=True)

    # Metadata (tags, related entity, etc.)
    metadata = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Document')
        verbose_name_plural = _('Documents')
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.unique_id} – {self.title}"

    def save(self, *args, **kwargs):
        if not self.unique_id:
            year = timezone.now().year
            count = Document.objects.filter(
                unique_id__startswith=f'DOC-{year}-'
            ).count()
            self.unique_id = f'DOC-{year}-{count + 1:06d}'

        # Auto-detect file type from extension
        if self.file and not self.file_type or self.file_type == self.FileType.OTHER:
            name = str(self.file.name).upper()
            if name.endswith('.PDF'):
                self.file_type = self.FileType.PDF
            elif name.endswith(('.JPG', '.JPEG')):
                self.file_type = self.FileType.JPG
            elif name.endswith('.PNG'):
                self.file_type = self.FileType.PNG
            elif name.endswith('.HEIC'):
                self.file_type = self.FileType.HEIC
            elif name.endswith('.TIFF'):
                self.file_type = self.FileType.TIFF
            elif name.endswith('.DOCX'):
                self.file_type = self.FileType.DOCX
            elif name.endswith('.XLSX'):
                self.file_type = self.FileType.XLSX

        super().save(*args, **kwargs)

    @property
    def file_size_human(self) -> str:
        """Human-readable file size."""
        if self.file_size < 1024:
            return f"{self.file_size} B"
        elif self.file_size < 1024 ** 2:
            return f"{self.file_size / 1024:.1f} KB"
        elif self.file_size < 1024 ** 3:
            return f"{self.file_size / (1024 ** 2):.1f} MB"
        return f"{self.file_size / (1024 ** 3):.1f} GB"

    @property
    def is_retention_expired(self) -> bool:
        return date.today() > self.retention_until

    @property
    def days_until_retention(self) -> int:
        delta = self.retention_until - date.today()
        return delta.days


class DocumentAuditLog(models.Model):
    """Immutable audit trail for document access and modifications."""

    class Action(models.TextChoices):
        UPLOADED = 'UPLOADED', _('Uploaded')
        VIEWED = 'VIEWED', _('Viewed / Downloaded')
        UPDATED = 'UPDATED', _('Updated')
        ARCHIVED = 'ARCHIVED', _('Archived')
        RESTORED = 'RESTORED', _('Restored from Archive')
        OCR_PROCESSED = 'OCR_PROCESSED', _('OCR Processed')
        DELETED = 'DELETED', _('Deleted')

    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name='audit_logs'
    )
    action = models.CharField(max_length=20, choices=Action.choices)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='document_audit_actions',
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        verbose_name = _('Document Audit Log')
        verbose_name_plural = _('Document Audit Logs')
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.document.unique_id} – {self.get_action_display()} at {self.timestamp}"
