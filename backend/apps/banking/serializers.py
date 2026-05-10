"""
Banking serializers: BankAccount, BankTransaction, ReconciliationSuggestion
"""
from rest_framework import serializers
from apps.accounts.serializers import UserSerializer
from apps.expenses.serializers import ExpenseSerializer
from .models import BankAccount, BankTransaction, ReconciliationSuggestion


class BankAccountSerializer(serializers.ModelSerializer):
    """Serializer for BankAccount."""
    owner_detail = UserSerializer(source='owner', read_only=True)
    transaction_count = serializers.SerializerMethodField()
    unreconciled_count = serializers.SerializerMethodField()

    class Meta:
        model = BankAccount
        fields = [
            'id', 'name', 'bank_name', 'iban', 'currency', 'account_type',
            'balance', 'last_synced_at', 'is_active', 'is_primary',
            'connection_status', 'api_provider', 'owner', 'owner_detail',
            'transaction_count', 'unreconciled_count', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'last_synced_at', 'created_at', 'updated_at']
        extra_kwargs = {
            'api_credentials_encrypted': {'write_only': True},
        }

    def get_transaction_count(self, obj):
        return obj.transactions.count()

    def get_unreconciled_count(self, obj):
        return obj.transactions.filter(is_reconciled=False, status='PENDING').count()

    def validate_iban(self, value):
        cleaned = value.upper().replace(' ', '')
        if len(cleaned) < 15 or len(cleaned) > 34:
            raise serializers.ValidationError('Invalid IBAN length.')
        return cleaned


class BankTransactionSerializer(serializers.ModelSerializer):
    """Serializer for BankTransaction."""
    bank_account_name = serializers.ReadOnlyField(source='bank_account.name')
    reconciled_expense_detail = serializers.SerializerMethodField()
    suggestion_count = serializers.SerializerMethodField()

    class Meta:
        model = BankTransaction
        fields = [
            'id', 'unique_id', 'bank_account', 'bank_account_name',
            'transaction_date', 'value_date', 'amount', 'currency',
            'transaction_type', 'description', 'reference',
            'counterparty_name', 'counterparty_iban',
            'is_reconciled', 'reconciled_expense', 'reconciled_expense_detail',
            'reconciliation_confidence', 'status',
            'suggestion_count', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'unique_id', 'is_reconciled', 'reconciled_expense',
            'reconciliation_confidence', 'status', 'created_at', 'updated_at',
        ]

    def get_reconciled_expense_detail(self, obj):
        if obj.reconciled_expense:
            return {
                'id': obj.reconciled_expense.id,
                'unique_id': obj.reconciled_expense.unique_id,
                'title': obj.reconciled_expense.title,
                'amount': str(obj.reconciled_expense.amount),
            }
        return None

    def get_suggestion_count(self, obj):
        return obj.suggestions.filter(status='PENDING').count()


class ReconciliationSuggestionSerializer(serializers.ModelSerializer):
    """Serializer for ReconciliationSuggestion."""
    transaction_detail = BankTransactionSerializer(source='transaction', read_only=True)
    expense_detail = serializers.SerializerMethodField()
    reviewed_by_detail = UserSerializer(source='reviewed_by', read_only=True)

    class Meta:
        model = ReconciliationSuggestion
        fields = [
            'id', 'transaction', 'transaction_detail',
            'expense', 'expense_detail',
            'confidence_score', 'status', 'match_reasons',
            'created_at', 'reviewed_at', 'reviewed_by', 'reviewed_by_detail',
        ]
        read_only_fields = [
            'id', 'confidence_score', 'match_reasons',
            'created_at', 'reviewed_at', 'reviewed_by',
        ]

    def get_expense_detail(self, obj):
        return {
            'id': obj.expense.id,
            'unique_id': obj.expense.unique_id,
            'title': obj.expense.title,
            'amount': str(obj.expense.amount),
            'vendor_name': obj.expense.vendor_name,
            'expense_date': str(obj.expense.expense_date),
            'status': obj.expense.status,
        }


class SyncRequestSerializer(serializers.Serializer):
    """Serializer for bank sync request."""
    account_id = serializers.IntegerField(required=False)
    sync_all = serializers.BooleanField(default=False)


class ReconciliationActionSerializer(serializers.Serializer):
    """Serializer for accepting/rejecting reconciliation suggestions."""
    suggestion_id = serializers.IntegerField()
    note = serializers.CharField(required=False, allow_blank=True, default='')
