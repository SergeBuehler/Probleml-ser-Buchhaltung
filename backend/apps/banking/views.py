"""
Banking views: BankAccount, BankTransaction, Reconciliation, Sync
"""
import logging

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from .models import BankAccount, BankTransaction, ReconciliationSuggestion
from .serializers import (
    BankAccountSerializer, BankTransactionSerializer,
    ReconciliationSuggestionSerializer, SyncRequestSerializer,
    ReconciliationActionSerializer,
)
from .services import ReconciliationService

logger = logging.getLogger(__name__)


class BankAccountViewSet(ModelViewSet):
    """
    CRUD for bank accounts.

    GET    /banking/accounts/        - list all
    POST   /banking/accounts/        - create
    GET    /banking/accounts/{id}/   - retrieve
    PUT    /banking/accounts/{id}/   - update
    PATCH  /banking/accounts/{id}/   - partial update
    DELETE /banking/accounts/{id}/   - delete
    POST   /banking/accounts/{id}/sync/ - trigger sync
    """
    serializer_class = BankAccountSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'is_primary', 'account_type', 'connection_status', 'api_provider']
    search_fields = ['name', 'bank_name', 'iban']
    ordering_fields = ['name', 'balance', 'last_synced_at']
    ordering = ['-is_primary', 'name']

    def get_queryset(self):
        return BankAccount.objects.select_related('owner').all()

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['post'], url_path='sync')
    def sync(self, request, pk=None):
        """Trigger bank synchronization for a specific account."""
        account = self.get_object()
        try:
            new_transactions = ReconciliationService.mock_bank_sync(account)
            return Response({
                'message': f'Sync completed for {account.name}.',
                'new_transactions': len(new_transactions),
                'account_id': account.id,
                'iban': account.iban,
                'last_synced_at': account.last_synced_at,
            })
        except Exception as e:
            logger.error(f"Bank sync failed for account {account.id}: {e}")
            return Response(
                {'error': f'Sync failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=['get'], url_path='transactions')
    def transactions(self, request, pk=None):
        """List transactions for a specific account."""
        account = self.get_object()
        txs = account.transactions.all().order_by('-transaction_date')
        page = self.paginate_queryset(txs)
        if page is not None:
            serializer = BankTransactionSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = BankTransactionSerializer(txs, many=True, context={'request': request})
        return Response(serializer.data)


class BankTransactionViewSet(ModelViewSet):
    """
    Read + manage bank transactions.

    GET    /banking/transactions/               - list
    GET    /banking/transactions/{id}/          - retrieve
    POST   /banking/transactions/{id}/reconcile/ - manually reconcile
    POST   /banking/transactions/{id}/ignore/   - mark as ignored
    GET    /banking/transactions/{id}/suggestions/ - list suggestions
    """
    serializer_class = BankTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'head', 'options']
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        'bank_account', 'transaction_type', 'status',
        'is_reconciled', 'currency', 'transaction_date',
    ]
    search_fields = [
        'description', 'reference', 'counterparty_name',
        'counterparty_iban', 'unique_id',
    ]
    ordering_fields = ['transaction_date', 'amount', 'created_at']
    ordering = ['-transaction_date']

    def get_queryset(self):
        return BankTransaction.objects.select_related(
            'bank_account', 'reconciled_expense'
        ).prefetch_related('suggestions')

    @action(detail=True, methods=['get'], url_path='suggestions')
    def suggestions(self, request, pk=None):
        """Get reconciliation suggestions for a transaction."""
        transaction = self.get_object()
        suggestions = transaction.suggestions.filter(
            status='PENDING'
        ).select_related('expense', 'reviewed_by').order_by('-confidence_score')
        serializer = ReconciliationSuggestionSerializer(
            suggestions, many=True, context={'request': request}
        )
        return Response({
            'transaction_id': transaction.id,
            'unique_id': transaction.unique_id,
            'suggestions': serializer.data,
        })

    @action(detail=True, methods=['post'], url_path='generate_suggestions')
    def generate_suggestions(self, request, pk=None):
        """Generate reconciliation suggestions for this transaction."""
        transaction = self.get_object()
        if transaction.is_reconciled:
            return Response(
                {'error': 'Transaction is already reconciled.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        suggestions = ReconciliationService.create_suggestions_for_transaction(transaction)
        serializer = ReconciliationSuggestionSerializer(
            suggestions, many=True, context={'request': request}
        )
        return Response({
            'message': f'{len(suggestions)} suggestions generated.',
            'suggestions': serializer.data,
        })

    @action(detail=True, methods=['post'], url_path='ignore')
    def ignore(self, request, pk=None):
        """Mark a transaction as ignored (e.g., internal transfer)."""
        transaction = self.get_object()
        transaction.status = BankTransaction.TransactionStatus.IGNORED
        transaction.save(update_fields=['status', 'updated_at'])
        return Response({'message': 'Transaction marked as ignored.'})

    @action(detail=True, methods=['post'], url_path='manual_reconcile')
    def manual_reconcile(self, request, pk=None):
        """Manually link a transaction to an expense."""
        from apps.expenses.models import Expense

        transaction = self.get_object()
        if transaction.is_reconciled:
            return Response(
                {'error': 'Transaction is already reconciled.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        expense_id = request.data.get('expense_id')
        if not expense_id:
            return Response(
                {'error': 'expense_id is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            expense = Expense.objects.get(pk=expense_id)
        except Expense.DoesNotExist:
            return Response({'error': 'Expense not found.'}, status=status.HTTP_404_NOT_FOUND)

        transaction.is_reconciled = True
        transaction.reconciled_expense = expense
        transaction.reconciliation_confidence = 1.0
        transaction.status = BankTransaction.TransactionStatus.RECONCILED
        transaction.save()

        if expense.status == 'APPROVED':
            expense.status = 'PAID'
            expense.paid_date = transaction.transaction_date
            expense.save(update_fields=['status', 'paid_date', 'updated_at'])

        return Response({
            'message': 'Transaction manually reconciled.',
            'transaction': BankTransactionSerializer(transaction, context={'request': request}).data,
        })


class ReconciliationView(APIView):
    """
    List suggestions, accept or reject them.

    GET  /banking/reconciliation/                    - list all pending suggestions
    POST /banking/reconciliation/accept/             - accept a suggestion
    POST /banking/reconciliation/reject/             - reject a suggestion
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """List pending reconciliation suggestions."""
        qs = ReconciliationSuggestion.objects.filter(
            status='PENDING'
        ).select_related(
            'transaction', 'expense', 'reviewed_by'
        ).order_by('-confidence_score', '-created_at')

        # Filter by account if requested
        account_id = request.query_params.get('account_id')
        if account_id:
            qs = qs.filter(transaction__bank_account_id=account_id)

        page_size = int(request.query_params.get('page_size', 25))
        page = int(request.query_params.get('page', 1))
        offset = (page - 1) * page_size
        total = qs.count()
        items = qs[offset:offset + page_size]

        serializer = ReconciliationSuggestionSerializer(
            items, many=True, context={'request': request}
        )
        return Response({
            'count': total,
            'page': page,
            'page_size': page_size,
            'results': serializer.data,
        })


class ReconciliationAcceptView(APIView):
    """Accept a reconciliation suggestion."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ReconciliationActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        suggestion_id = serializer.validated_data['suggestion_id']
        try:
            result = ReconciliationService.accept_match(suggestion_id, request.user)
            return Response({
                'message': 'Reconciliation accepted.',
                **result,
            })
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ReconciliationRejectView(APIView):
    """Reject a reconciliation suggestion."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ReconciliationActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        suggestion_id = serializer.validated_data['suggestion_id']
        try:
            result = ReconciliationService.reject_match(suggestion_id, request.user)
            return Response({
                'message': 'Reconciliation rejected.',
                **result,
            })
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SyncView(APIView):
    """
    Trigger bank synchronization.
    POST /banking/sync/
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = SyncRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        account_id = serializer.validated_data.get('account_id')
        sync_all = serializer.validated_data.get('sync_all', False)

        if account_id:
            accounts = BankAccount.objects.filter(pk=account_id, is_active=True)
        elif sync_all:
            accounts = BankAccount.objects.filter(is_active=True)
        else:
            return Response(
                {'error': 'Provide account_id or set sync_all=true.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        results = []
        for account in accounts:
            try:
                new_txs = ReconciliationService.mock_bank_sync(account)
                results.append({
                    'account_id': account.id,
                    'account_name': account.name,
                    'iban': account.iban,
                    'new_transactions': len(new_txs),
                    'status': 'success',
                })
            except Exception as e:
                results.append({
                    'account_id': account.id,
                    'account_name': account.name,
                    'iban': account.iban,
                    'error': str(e),
                    'status': 'error',
                })

        return Response({
            'message': f'Sync completed for {len(results)} account(s).',
            'results': results,
        })
