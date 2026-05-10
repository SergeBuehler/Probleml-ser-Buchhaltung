"""
Properties models: Property, PropertyDocument, PropertyHistory
"""
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Property(models.Model):
    """Represents a managed property with fee and assignment details."""

    unique_id = models.CharField(max_length=30, unique=True, blank=True, db_index=True)
    name = models.CharField(max_length=200)
    address = models.TextField()
    description = models.TextField(blank=True, default='')
    assigned_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='managed_properties',
        help_text='The manager responsible for this property.',
    )
    annual_management_fee = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text='Annual management fee in CHF.',
    )
    management_start_date = models.DateField(
        help_text='Date the management agreement began (takeover date).'
    )
    management_end_date = models.DateField(
        null=True, blank=True,
        help_text='Date the management agreement ended, if applicable.',
    )
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_properties',
    )

    class Meta:
        verbose_name = _('Property')
        verbose_name_plural = _('Properties')
        ordering = ['name']

    def __str__(self):
        return f"{self.unique_id} – {self.name}"

    def save(self, *args, **kwargs):
        if not self.unique_id:
            year = timezone.now().year
            count = Property.objects.filter(
                unique_id__startswith=f'PROP-{year}-'
            ).count()
            self.unique_id = f'PROP-{year}-{count + 1:06d}'
        super().save(*args, **kwargs)


class PropertyDocument(models.Model):
    """Documents attached to a property."""

    class DocumentType(models.TextChoices):
        CONTRACT = 'CONTRACT', _('Management Contract')
        FLOOR_PLAN = 'FLOOR_PLAN', _('Floor Plan')
        INSURANCE = 'INSURANCE', _('Insurance Document')
        INSPECTION = 'INSPECTION', _('Inspection Report')
        CORRESPONDENCE = 'CORRESPONDENCE', _('Correspondence')
        OTHER = 'OTHER', _('Other')

    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name='documents'
    )
    file = models.FileField(upload_to='property_documents/%Y/%m/')
    document_type = models.CharField(
        max_length=30, choices=DocumentType.choices, default=DocumentType.OTHER
    )
    description = models.CharField(max_length=300, blank=True, default='')
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True,
        related_name='uploaded_property_documents',
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Property Document')
        verbose_name_plural = _('Property Documents')
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.property.name} – {self.get_document_type_display()}"


class PropertyHistory(models.Model):
    """Audit trail for property changes."""

    class ChangeType(models.TextChoices):
        CREATED = 'CREATED', _('Created')
        UPDATED = 'UPDATED', _('Updated')
        FEE_CHANGED = 'FEE_CHANGED', _('Fee Changed')
        MANAGER_CHANGED = 'MANAGER_CHANGED', _('Manager Changed')
        DEACTIVATED = 'DEACTIVATED', _('Deactivated')
        REACTIVATED = 'REACTIVATED', _('Reactivated')

    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name='history'
    )
    change_type = models.CharField(max_length=30, choices=ChangeType.choices)
    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True,
        related_name='property_changes',
    )
    changed_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = _('Property History')
        verbose_name_plural = _('Property Histories')
        ordering = ['-changed_at']

    def __str__(self):
        return f"{self.property.name} – {self.get_change_type_display()} at {self.changed_at}"
