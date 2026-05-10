"""
Accounting models: AccountingEntry, FiscalYear
"""
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class FiscalYear(models.Model):
    """Represents an accounting fiscal year with year-end closing status."""

    class Status(models.TextChoices):
        OPEN = 'OPEN', _('Open')
        CLOSING = 'CLOSING', _('Year-End Closing in Progress')
        CLOSED = 'CLOSED', _('Closed')

    year = models.IntegerField(unique=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.OPEN
    )
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='closed_fiscal_years',
    )

    # Frozen snapshots at year-end
    revenue_percentages_snapshot = models.JSONField(
        null=True, blank=True,
        help_text='Revenue split percentages frozen at year-end closing.'
    )
    total_revenue_a = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
        help_text='Total revenue attributed to Manager A.'
    )
    total_revenue_b = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
        help_text='Total revenue attributed to Manager B.'
    )
    total_expenses = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_payroll = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Fiscal Year')
        verbose_name_plural = _('Fiscal Years')
        ordering = ['-year']

    def __str__(self):
        return f"Fiscal Year {self.year} ({self.get_status_display()})"

    @property
    def is_closed(self):
        return self.status == self.Status.CLOSED

    @classmethod
    def get_or_create_current(cls):
        """Get or create fiscal year for the current calendar year."""
        year = timezone.now().year
        fy, _ = cls.objects.get_or_create(year=year, defaults={'status': cls.Status.OPEN})
        return fy


class AccountingEntry(models.Model):
    """Double-entry accounting record for audit trail."""

    class EntryType(models.TextChoices):
        REVENUE = 'REVENUE', _('Revenue')
        EXPENSE = 'EXPENSE', _('Expense')
        PAYROLL = 'PAYROLL', _('Payroll')
        ADJUSTMENT = 'ADJUSTMENT', _('Adjustment / Correction')
        PROVISION = 'PROVISION', _('Provision / Accrual')
        TRANSFER = 'TRANSFER', _('Internal Transfer')

    unique_id = models.CharField(max_length=30, unique=True, blank=True, db_index=True)
    entry_type = models.CharField(max_length=20, choices=EntryType.choices)
    description = models.TextField()
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default='CHF')
    date = models.DateField()
    fiscal_year = models.ForeignKey(
        FiscalYear,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='entries',
    )
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='accounting_entries',
    )
    expense = models.ForeignKey(
        'expenses.Expense',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='accounting_entries',
    )
    payroll_period = models.ForeignKey(
        'payroll.PayrollPeriod',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='accounting_entries',
    )
    is_closed = models.BooleanField(
        default=False,
        help_text='Frozen after fiscal year-end. Cannot be modified.'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_accounting_entries',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reference = models.CharField(max_length=200, blank=True, default='')
    notes = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = _('Accounting Entry')
        verbose_name_plural = _('Accounting Entries')
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.unique_id} – {self.get_entry_type_display()} {self.amount} CHF on {self.date}"

    def save(self, *args, **kwargs):
        if not self.unique_id:
            year = timezone.now().year
            count = AccountingEntry.objects.filter(
                unique_id__startswith=f'ACC-{year}-'
            ).count()
            self.unique_id = f'ACC-{year}-{count + 1:06d}'
        if self.is_closed:
            # Prevent modification of closed entries
            if self.pk:
                original = AccountingEntry.objects.filter(pk=self.pk, is_closed=True).first()
                if original:
                    raise ValueError(
                        f"Accounting entry {self.unique_id} is closed and cannot be modified."
                    )
        super().save(*args, **kwargs)
