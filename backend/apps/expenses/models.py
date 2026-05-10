"""
Expenses models: Expense, ExpenseAllocation, ExpenseAuditLog
"""
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Expense(models.Model):
    """Represents a business expense with OCR, QR-bill and allocation support."""

    class Category(models.TextChoices):
        OFFICE = 'OFFICE', _('Office Supplies')
        TRAVEL = 'TRAVEL', _('Travel & Transport')
        MEALS = 'MEALS', _('Meals & Entertainment')
        SOFTWARE = 'SOFTWARE', _('Software & Licenses')
        HARDWARE = 'HARDWARE', _('Hardware & Equipment')
        INSURANCE = 'INSURANCE', _('Insurance')
        BANKING = 'BANKING', _('Banking & Finance')
        PAYROLL = 'PAYROLL', _('Payroll Related')
        MAINTENANCE = 'MAINTENANCE', _('Maintenance & Repairs')
        MARKETING = 'MARKETING', _('Marketing & Advertising')
        LEGAL = 'LEGAL', _('Legal & Professional')
        OTHER = 'OTHER', _('Other')

    class AllocationMethod(models.TextChoices):
        MANAGER_A = 'MANAGER_A', _('100% Manager A')
        MANAGER_B = 'MANAGER_B', _('100% Manager B')
        FIFTY_FIFTY = 'FIFTY_FIFTY', _('50% / 50%')
        REVENUE_BASED = 'REVENUE_BASED', _('Revenue-Proportional')

    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pending Review')
        APPROVED = 'APPROVED', _('Approved')
        PAID = 'PAID', _('Paid')
        REJECTED = 'REJECTED', _('Rejected')

    class Currency(models.TextChoices):
        CHF = 'CHF', _('Swiss Franc')
        EUR = 'EUR', _('Euro')
        USD = 'USD', _('US Dollar')

    unique_id = models.CharField(max_length=30, unique=True, blank=True, db_index=True)
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True, default='')

    # Financial fields
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.CHF)
    vat_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Dates
    expense_date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    paid_date = models.DateField(null=True, blank=True)

    # Classification
    category = models.CharField(
        max_length=20, choices=Category.choices, default=Category.OTHER
    )
    allocation_method = models.CharField(
        max_length=20,
        choices=AllocationMethod.choices,
        default=AllocationMethod.FIFTY_FIFTY,
    )
    allocation_note = models.TextField(blank=True, default='')
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_expenses',
    )

    # Vendor / payment info
    vendor_name = models.CharField(max_length=200, blank=True, default='')
    vendor_iban = models.CharField(max_length=34, blank=True, default='')
    payment_reference = models.CharField(max_length=200, blank=True, default='')

    # Receipt & OCR
    receipt_file = models.FileField(
        upload_to='receipts/%Y/%m/', null=True, blank=True
    )

    # Swiss QR-bill fields
    is_qr_bill = models.BooleanField(default=False)
    qr_reference = models.CharField(max_length=50, blank=True, default='')
    qr_creditor_iban = models.CharField(max_length=34, blank=True, default='')

    # OCR data
    ocr_raw_data = models.JSONField(null=True, blank=True)
    ocr_extracted_data = models.JSONField(null=True, blank=True)
    ocr_confidence_score = models.FloatField(null=True, blank=True)
    is_ocr_reviewed = models.BooleanField(default=False)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Expense')
        verbose_name_plural = _('Expenses')
        ordering = ['-expense_date', '-created_at']

    def __str__(self):
        return f"{self.unique_id} – {self.title} ({self.amount} {self.currency})"

    def save(self, *args, **kwargs):
        if not self.unique_id:
            year = timezone.now().year
            count = Expense.objects.filter(
                unique_id__startswith=f'EXP-{year}-'
            ).count()
            self.unique_id = f'EXP-{year}-{count + 1:06d}'
        # Auto-calculate net amount if not set
        if self.net_amount == 0 and self.amount and self.vat_amount:
            self.net_amount = self.amount - self.vat_amount
        elif self.net_amount == 0 and self.amount:
            self.net_amount = self.amount
        super().save(*args, **kwargs)


class ExpenseAllocation(models.Model):
    """Allocation of an expense amount to a specific manager."""

    class AllocationType(models.TextChoices):
        FIXED = 'FIXED', _('Fixed Amount')
        PERCENTAGE = 'PERCENTAGE', _('Percentage-Based')
        REVENUE = 'REVENUE', _('Revenue-Proportional')

    expense = models.ForeignKey(
        Expense, on_delete=models.CASCADE, related_name='allocations'
    )
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='expense_allocations',
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    percentage = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    allocation_type = models.CharField(
        max_length=20,
        choices=AllocationType.choices,
        default=AllocationType.PERCENTAGE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Expense Allocation')
        verbose_name_plural = _('Expense Allocations')
        unique_together = ('expense', 'manager')
        ordering = ['manager']

    def __str__(self):
        return f"{self.expense.unique_id} → {self.manager.full_name}: {self.amount} CHF ({self.percentage}%)"


class ExpenseAuditLog(models.Model):
    """Immutable audit trail for all expense changes."""

    class Action(models.TextChoices):
        CREATED = 'CREATED', _('Created')
        UPDATED = 'UPDATED', _('Updated')
        APPROVED = 'APPROVED', _('Approved')
        REJECTED = 'REJECTED', _('Rejected')
        PAID = 'PAID', _('Marked as Paid')
        OCR_PROCESSED = 'OCR_PROCESSED', _('OCR Processed')
        ALLOCATED = 'ALLOCATED', _('Allocated')
        BULK_UPLOADED = 'BULK_UPLOADED', _('Bulk Uploaded')

    expense = models.ForeignKey(
        Expense, on_delete=models.CASCADE, related_name='audit_logs'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='expense_audit_actions',
    )
    action = models.CharField(max_length=30, choices=Action.choices)
    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    notes = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = _('Expense Audit Log')
        verbose_name_plural = _('Expense Audit Logs')
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.expense.unique_id} – {self.get_action_display()} at {self.timestamp}"
