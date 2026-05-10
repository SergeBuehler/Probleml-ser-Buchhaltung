"""
Banking reconciliation service.
Matches bank transactions to expenses using weighted scoring.
"""
import logging
from datetime import date, timedelta
from decimal import Decimal
from difflib import SequenceMatcher
from typing import List, Tuple

logger = logging.getLogger(__name__)


def _string_similarity(a: str, b: str) -> float:
    """Return similarity ratio between two strings (0.0 to 1.0)."""
    if not a or not b:
        return 0.0
    a = a.lower().strip()
    b = b.lower().strip()
    return SequenceMatcher(None, a, b).ratio()


def _date_proximity_score(date1: date, date2: date, max_days: int = 30) -> float:
    """
    Score date proximity. Returns 1.0 if same day, 0.0 if difference >= max_days.
    """
    diff = abs((date1 - date2).days)
    if diff == 0:
        return 1.0
    if diff >= max_days:
        return 0.0
    return 1.0 - (diff / max_days)


def _amount_match_score(amount1: Decimal, amount2: Decimal) -> float:
    """
    Score amount match. 1.0 for exact match, scaled down for small differences.
    """
    if amount1 == amount2:
        return 1.0
    if amount1 == 0 or amount2 == 0:
        return 0.0
    diff = abs(amount1 - amount2)
    # Allow up to 5% difference
    tolerance = max(amount1, amount2) * Decimal('0.05')
    if diff > tolerance:
        return 0.0
    return float(1 - diff / tolerance)


def _reference_match_score(ref1: str, ref2: str) -> float:
    """Check if references overlap."""
    if not ref1 or not ref2:
        return 0.0
    ref1 = ref1.lower().replace(' ', '').replace('-', '')
    ref2 = ref2.lower().replace(' ', '').replace('-', '')
    if ref1 in ref2 or ref2 in ref1:
        return 1.0
    return _string_similarity(ref1, ref2)


class ReconciliationService:
    """
    Matches bank transactions to expenses using a weighted scoring algorithm.

    Weights:
    - Amount exact match: 0.40
    - Vendor name similarity: 0.30
    - Date proximity (within 30 days): 0.20
    - Reference/description match: 0.10
    """

    AMOUNT_WEIGHT = 0.40
    VENDOR_WEIGHT = 0.30
    DATE_WEIGHT = 0.20
    REFERENCE_WEIGHT = 0.10
    MIN_CONFIDENCE_THRESHOLD = 0.30

    @classmethod
    def suggest_matches(
        cls, transaction, max_suggestions: int = 5
    ) -> List[Tuple]:
        """
        Find candidate expenses for a bank transaction.

        Args:
            transaction: BankTransaction instance
            max_suggestions: maximum number of suggestions to return

        Returns:
            List of (expense, confidence_score, match_reasons) tuples, sorted by confidence.
        """
        from apps.expenses.models import Expense

        # Only consider DEBIT transactions for expense matching
        if transaction.transaction_type != 'DEBIT':
            return []

        # Look for unreconciled, approved/paid expenses within 60 days
        tx_date = transaction.transaction_date
        date_range_start = tx_date - timedelta(days=60)
        date_range_end = tx_date + timedelta(days=10)

        candidates = Expense.objects.filter(
            expense_date__gte=date_range_start,
            expense_date__lte=date_range_end,
            status__in=['APPROVED', 'PAID', 'PENDING'],
        ).exclude(
            bank_transactions__is_reconciled=True
        )

        results = []

        for expense in candidates:
            score, reasons = cls._score_match(transaction, expense)
            if score >= cls.MIN_CONFIDENCE_THRESHOLD:
                results.append((expense, score, reasons))

        # Sort by confidence descending
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:max_suggestions]

    @classmethod
    def _score_match(cls, transaction, expense) -> Tuple[float, dict]:
        """
        Compute weighted confidence score for transaction-expense pair.

        Returns:
            (score: float, reasons: dict)
        """
        tx_amount = abs(transaction.amount)
        exp_amount = expense.amount

        amount_score = _amount_match_score(tx_amount, exp_amount)
        vendor_score = _string_similarity(
            transaction.counterparty_name, expense.vendor_name
        )
        date_score = _date_proximity_score(
            transaction.transaction_date, expense.expense_date
        )
        ref_score = _reference_match_score(
            transaction.reference + ' ' + transaction.description,
            expense.payment_reference + ' ' + expense.vendor_name,
        )

        total_score = (
            amount_score * cls.AMOUNT_WEIGHT
            + vendor_score * cls.VENDOR_WEIGHT
            + date_score * cls.DATE_WEIGHT
            + ref_score * cls.REFERENCE_WEIGHT
        )

        reasons = {
            'amount_score': round(amount_score, 4),
            'vendor_score': round(vendor_score, 4),
            'date_score': round(date_score, 4),
            'reference_score': round(ref_score, 4),
            'total_score': round(total_score, 4),
            'tx_amount': str(tx_amount),
            'exp_amount': str(exp_amount),
            'date_diff_days': abs((transaction.transaction_date - expense.expense_date).days),
        }

        return round(total_score, 4), reasons

    @classmethod
    def create_suggestions_for_transaction(cls, transaction) -> List:
        """
        Generate and save ReconciliationSuggestion objects for a transaction.

        Returns:
            List of created ReconciliationSuggestion instances.
        """
        from apps.banking.models import ReconciliationSuggestion

        matches = cls.suggest_matches(transaction)
        created = []

        for expense, confidence, reasons in matches:
            suggestion, _ = ReconciliationSuggestion.objects.get_or_create(
                transaction=transaction,
                expense=expense,
                defaults={
                    'confidence_score': confidence,
                    'match_reasons': reasons,
                    'status': ReconciliationSuggestion.SuggestionStatus.PENDING,
                }
            )
            # Update confidence if already exists
            if suggestion.status == ReconciliationSuggestion.SuggestionStatus.PENDING:
                suggestion.confidence_score = confidence
                suggestion.match_reasons = reasons
                suggestion.save(update_fields=['confidence_score', 'match_reasons'])
            created.append(suggestion)

        logger.info(
            f"Created {len(created)} reconciliation suggestions for "
            f"transaction {transaction.unique_id}."
        )
        return created

    @classmethod
    def accept_match(cls, suggestion_id: int, user) -> dict:
        """
        Accept a reconciliation suggestion.
        Marks the transaction as reconciled and the expense as paid.

        Returns:
            dict with transaction and expense details.
        """
        from apps.banking.models import ReconciliationSuggestion
        from django.utils import timezone

        try:
            suggestion = ReconciliationSuggestion.objects.select_related(
                'transaction', 'expense'
            ).get(pk=suggestion_id)
        except ReconciliationSuggestion.DoesNotExist:
            raise ValueError(f"Suggestion {suggestion_id} not found.")

        if suggestion.status != ReconciliationSuggestion.SuggestionStatus.PENDING:
            raise ValueError(
                f"Suggestion {suggestion_id} is already {suggestion.status}."
            )

        # Update suggestion
        suggestion.status = ReconciliationSuggestion.SuggestionStatus.ACCEPTED
        suggestion.reviewed_at = timezone.now()
        suggestion.reviewed_by = user
        suggestion.save()

        # Update transaction
        tx = suggestion.transaction
        tx.is_reconciled = True
        tx.reconciled_expense = suggestion.expense
        tx.reconciliation_confidence = suggestion.confidence_score
        tx.status = 'RECONCILED'
        tx.save(update_fields=[
            'is_reconciled', 'reconciled_expense',
            'reconciliation_confidence', 'status', 'updated_at',
        ])

        # Update expense to PAID if not already
        expense = suggestion.expense
        if expense.status == 'APPROVED':
            expense.status = 'PAID'
            expense.paid_date = tx.transaction_date
            expense.save(update_fields=['status', 'paid_date', 'updated_at'])

        # Reject other pending suggestions for this transaction
        ReconciliationSuggestion.objects.filter(
            transaction=tx,
            status=ReconciliationSuggestion.SuggestionStatus.PENDING,
        ).exclude(pk=suggestion_id).update(
            status=ReconciliationSuggestion.SuggestionStatus.REJECTED
        )

        logger.info(
            f"Reconciliation accepted: {tx.unique_id} ↔ {expense.unique_id} "
            f"by {user.email}."
        )

        return {
            'transaction_id': tx.id,
            'transaction_unique_id': tx.unique_id,
            'expense_id': expense.id,
            'expense_unique_id': expense.unique_id,
            'confidence_score': suggestion.confidence_score,
        }

    @classmethod
    def reject_match(cls, suggestion_id: int, user) -> dict:
        """
        Reject a reconciliation suggestion.

        Returns:
            dict with updated suggestion info.
        """
        from apps.banking.models import ReconciliationSuggestion
        from django.utils import timezone

        try:
            suggestion = ReconciliationSuggestion.objects.select_related(
                'transaction', 'expense'
            ).get(pk=suggestion_id)
        except ReconciliationSuggestion.DoesNotExist:
            raise ValueError(f"Suggestion {suggestion_id} not found.")

        suggestion.status = ReconciliationSuggestion.SuggestionStatus.REJECTED
        suggestion.reviewed_at = timezone.now()
        suggestion.reviewed_by = user
        suggestion.save()

        logger.info(
            f"Reconciliation rejected: suggestion {suggestion_id} by {user.email}."
        )

        return {
            'suggestion_id': suggestion.id,
            'status': suggestion.status,
            'transaction_unique_id': suggestion.transaction.unique_id,
            'expense_unique_id': suggestion.expense.unique_id,
        }

    @classmethod
    def mock_bank_sync(cls, bank_account) -> List:
        """
        Mock bank sync: generate dummy transactions for testing.
        In production this would call the bank's Open Banking API.

        Returns:
            List of created BankTransaction instances.
        """
        from apps.banking.models import BankTransaction
        from django.utils import timezone
        import random
        from datetime import date, timedelta

        today = date.today()
        created = []

        mock_transactions_data = [
            {
                'transaction_date': today - timedelta(days=1),
                'amount': Decimal('-1250.00'),
                'transaction_type': BankTransaction.TransactionType.DEBIT,
                'description': 'Büromaterial Migros',
                'counterparty_name': 'Migros Zürich AG',
                'reference': 'INV-2026-001',
            },
            {
                'transaction_date': today - timedelta(days=2),
                'amount': Decimal('12000.00'),
                'transaction_type': BankTransaction.TransactionType.CREDIT,
                'description': 'Verwaltungsgebühr Objekt Musterstrasse',
                'counterparty_name': 'Müller Peter',
                'reference': 'VEW-2026-003',
            },
            {
                'transaction_date': today - timedelta(days=5),
                'amount': Decimal('-456.80'),
                'transaction_type': BankTransaction.TransactionType.DEBIT,
                'description': 'Swisscom Rechnung März 2026',
                'counterparty_name': 'Swisscom AG',
                'reference': 'SC-4567891',
            },
        ]

        for data in mock_transactions_data:
            # Avoid duplicate imports using external_id
            ext_id = f"mock-{bank_account.id}-{data['transaction_date']}-{data['amount']}"
            if BankTransaction.objects.filter(external_id=ext_id).exists():
                continue

            tx = BankTransaction.objects.create(
                bank_account=bank_account,
                external_id=ext_id,
                value_date=data['transaction_date'],
                currency=bank_account.currency,
                **data,
            )
            created.append(tx)
            # Auto-generate suggestions for debit transactions
            if tx.transaction_type == BankTransaction.TransactionType.DEBIT:
                cls.create_suggestions_for_transaction(tx)

        # Update account last sync time
        from django.utils import timezone
        bank_account.last_synced_at = timezone.now()
        bank_account.connection_status = 'CONNECTED'
        bank_account.save(update_fields=['last_synced_at', 'connection_status', 'updated_at'])

        logger.info(
            f"Mock sync for account {bank_account.iban}: {len(created)} new transactions."
        )
        return created
