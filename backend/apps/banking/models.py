"""
Banking models: BankAccount, BankTransaction, ReconciliationSuggestion
"""
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class BankAccount(models.Model):
    """Represents a connected bank account."""

    class AccountType(models.TextChoices):
        BUSINESS = 'BUSINESS', _('Business Account')
        PERSONAL = 'PERSONAL', _('Personal Account')
        SAVINGS = 'SAVINGS', _('Savings Account')

    class ConnectionStatus(models.TextChoices):
        CONNECTED = 'CONNECTED', _('Connected')
        DISCONNECTED = 'DISCONNECTED', _('Disconnected')
        ERROR = 'ERROR', _('Connection Error')
        PENDING = 'PENDING', _('Pending Setup')

    class APIProvider(models.TextChoices):
        BLINK = 'BLINK', _('Blink by Bank CIC')
        UBS = 'UBS', _('UBS Open Banking')
        POSTFINANCE = 'POSTFINANCE', _('PostFinance')
        RAIFFEISEN = 'RAIFFEISEN', _('Raiffeisen')
        ZUERCHER_KB = 'ZUERCHER_KB', _('Zürcher Kantonalbank')
        OTHER = 'OTHER', _('Other')

    name = models.CharField(max_length=200)
    bank_name = models.CharField(max_length=200)
    iban = models.CharField(max_length=34, unique=True)
    currency = models.CharField(max_length=3, default='CHF')
    account_type = models.CharField(
        max_length=20, choices=AccountType.choices, default=AccountType.BUSINESS
    )
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_primary = models.BooleanField(default=False)
    connection_status = models.CharField(
        max_length=20, choices=ConnectionStatus.choices, default=ConnectionStatus.DISCONNECTED
    )
    api_provider = models.CharField(
        max_length=20, choices=APIProvider.choices, default=APIProvider.OTHER
    )
    api_credentials_encrypted = models.TextField(blank=True, default='')
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='bank_accounts',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Bank Account')
        verbose_name_plural = _('Bank Accounts')
        ordering = ['-is_primary', 'name']

    def __str__(self):
        return f"{self.name} ({self.iban})"


class BankTransaction(models.Model):
    """Represents a single bank transaction imported from Open Banking."""

    class TransactionType(models.TextChoices):
        CREDIT = 'CREDIT', _('Credit (incoming)')
        DEBIT = 'DEBIT', _('Debit (outgoing)')

    class TransactionStatus(models.TextChoices):
        PENDING = 'PENDING', _('Pending Reconciliation')
        RECONCILED = 'RECONCILED', _('Reconciled with Expense')
        UNMATCHED = 'UNMATCHED', _('No Match Found')
        IGNORED = 'IGNORED', _('Ignored / Internal Transfer')

    unique_id = models.CharField(max_length=30, unique=True, blank=True, db_index=True)
    bank_account = models.ForeignKey(
        BankAccount, on_delete=models.CASCADE, related_name='transactions'
    )
    transaction_date = models.DateField()
    value_date = models.DateField(null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='CHF')
    transaction_type = models.CharField(
        max_length=10, choices=TransactionType.choices
    )
    description = models.TextField(blank=True, default='')
    reference = models.CharField(max_length=300, blank=True, default='')
    counterparty_name = models.CharField(max_length=300, blank=True, default='')
    counterparty_iban = models.CharField(max_length=34, blank=True, default='')

    # Reconciliation
    is_reconciled = models.BooleanField(default=False)
    reconciled_expense = models.ForeignKey(
        'expenses.Expense',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='bank_transactions',
    )
    reconciliation_confidence = models.FloatField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=TransactionStatus.choices, default=TransactionStatus.PENDING
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # External bank ID to avoid duplicate imports
    external_id = models.CharField(max_length=200, blank=True, default='', db_index=True)

    class Meta:
        verbose_name = _('Bank Transaction')
        verbose_name_plural = _('Bank Transactions')
        ordering = ['-transaction_date', '-created_at']

    def __str__(self):
        return f"{self.unique_id} – {self.transaction_type} {self.amount} {self.currency}"

    def save(self, *args, **kwargs):
        if not self.unique_id:
            year = timezone.now().year
            count = BankTransaction.objects.filter(
                unique_id__startswith=f'TRX-{year}-'
            ).count()
            self.unique_id = f'TRX-{year}-{count + 1:06d}'
        super().save(*args, **kwargs)


class ReconciliationSuggestion(models.Model):
    """AI/rule-based suggestion linking a bank transaction to an expense."""

    class SuggestionStatus(models.TextChoices):
        PENDING = 'PENDING', _('Awaiting Review')
        ACCEPTED = 'ACCEPTED', _('Accepted')
        REJECTED = 'REJECTED', _('Rejected')

    transaction = models.ForeignKey(
        BankTransaction, on_delete=models.CASCADE, related_name='suggestions'
    )
    expense = models.ForeignKey(
        'expenses.Expense', on_delete=models.CASCADE, related_name='reconciliation_suggestions'
    )
    confidence_score = models.FloatField(default=0.0)
    status = models.CharField(
        max_length=20, choices=SuggestionStatus.choices, default=SuggestionStatus.PENDING
    )
    match_reasons = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reviewed_reconciliations',
    )

    class Meta:
        verbose_name = _('Reconciliation Suggestion')
        verbose_name_plural = _('Reconciliation Suggestions')
        ordering = ['-confidence_score', '-created_at']
        unique_together = ('transaction', 'expense')

    def __str__(self):
        return (
            f"Suggestion: {self.transaction.unique_id} ↔ {self.expense.unique_id} "
            f"({self.confidence_score:.2%})"
        )
