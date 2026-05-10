"""
Expenses views: CRUD, bulk upload, approve/reject, OCR processing, allocations.
"""
import logging
import random
from datetime import date, timedelta

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from .models import Expense, ExpenseAllocation, ExpenseAuditLog
from .serializers import (
    ExpenseSerializer, ExpenseDetailSerializer,
    ExpenseAllocationSerializer, ExpenseAuditLogSerializer,
    ExpenseStatusUpdateSerializer, OCRResultSerializer,
)
from .services import ExpenseAllocationService, get_client_ip

logger = logging.getLogger(__name__)


class ExpenseViewSet(ModelViewSet):
    """
    Full CRUD for expenses with approve/reject actions.

    GET    /expenses/                       - list
    POST   /expenses/                       - create
    GET    /expenses/{id}/                  - retrieve
    PUT    /expenses/{id}/                  - update
    PATCH  /expenses/{id}/                  - partial update
    DELETE /expenses/{id}/                  - delete
    POST   /expenses/{id}/approve/          - approve
    POST   /expenses/{id}/reject/           - reject
    POST   /expenses/{id}/mark_paid/        - mark as paid
    POST   /expenses/{id}/allocate/         - trigger allocation
    POST   /expenses/bulk_create/           - bulk create
    GET    /expenses/summary/               - year summary
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        'status', 'category', 'allocation_method', 'currency',
        'expense_date', 'is_qr_bill', 'is_ocr_reviewed',
    ]
    search_fields = ['title', 'description', 'vendor_name', 'unique_id', 'payment_reference']
    ordering_fields = ['expense_date', 'amount', 'created_at', 'status', 'category']
    ordering = ['-expense_date']

    def get_queryset(self):
        qs = Expense.objects.select_related('created_by').prefetch_related(
            'allocations', 'allocations__manager'
        )
        year = self.request.query_params.get('year')
        if year:
            try:
                qs = qs.filter(expense_date__year=int(year))
            except ValueError:
                pass
        return qs

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ExpenseDetailSerializer
        return ExpenseSerializer

    def perform_create(self, serializer):
        expense = serializer.save(created_by=self.request.user)
        ExpenseAuditLog.objects.create(
            expense=expense,
            user=self.request.user,
            action=ExpenseAuditLog.Action.CREATED,
            new_value={
                'title': expense.title,
                'amount': str(expense.amount),
                'expense_date': str(expense.expense_date),
            },
            ip_address=get_client_ip(self.request),
        )
        # Auto-allocate on creation
        try:
            ExpenseAllocationService.allocate_expense(expense)
        except Exception as e:
            logger.warning(f"Auto-allocation failed for {expense.unique_id}: {e}")
        logger.info(f"Expense created: {expense.unique_id} by {self.request.user.email}")

    def perform_update(self, serializer):
        old = self.get_object()
        old_data = {
            'title': old.title,
            'amount': str(old.amount),
            'status': old.status,
            'allocation_method': old.allocation_method,
        }
        expense = serializer.save()
        ExpenseAuditLog.objects.create(
            expense=expense,
            user=self.request.user,
            action=ExpenseAuditLog.Action.UPDATED,
            old_value=old_data,
            new_value={
                'title': expense.title,
                'amount': str(expense.amount),
                'status': expense.status,
                'allocation_method': expense.allocation_method,
            },
            ip_address=get_client_ip(self.request),
        )
        # Re-allocate if allocation method or amount changed
        if (old.allocation_method != expense.allocation_method or
                old.amount != expense.amount):
            try:
                ExpenseAllocationService.allocate_expense(expense)
            except Exception as e:
                logger.warning(f"Re-allocation failed for {expense.unique_id}: {e}")

    def perform_destroy(self, instance):
        ExpenseAuditLog.objects.create(
            expense=instance,
            user=self.request.user,
            action=ExpenseAuditLog.Action.UPDATED,
            old_value={'status': instance.status, 'title': instance.title},
            new_value={'deleted': True},
            ip_address=get_client_ip(self.request),
        )
        instance.delete()

    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        """Approve an expense."""
        expense = self.get_object()
        if expense.status not in [Expense.Status.PENDING]:
            return Response(
                {'error': f'Cannot approve expense with status {expense.status}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = ExpenseStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        old_status = expense.status
        expense.status = Expense.Status.APPROVED
        expense.save(update_fields=['status', 'updated_at'])

        ExpenseAuditLog.objects.create(
            expense=expense,
            user=request.user,
            action=ExpenseAuditLog.Action.APPROVED,
            old_value={'status': old_status},
            new_value={'status': expense.status, 'note': serializer.validated_data.get('note', '')},
            ip_address=get_client_ip(request),
        )
        # Ensure allocation exists
        if not expense.allocations.exists():
            ExpenseAllocationService.allocate_expense(expense)

        return Response(
            {'message': 'Expense approved.', 'expense': ExpenseSerializer(expense, context={'request': request}).data},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        """Reject an expense."""
        expense = self.get_object()
        if expense.status == Expense.Status.PAID:
            return Response(
                {'error': 'Cannot reject an already paid expense.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = ExpenseStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        old_status = expense.status
        expense.status = Expense.Status.REJECTED
        expense.save(update_fields=['status', 'updated_at'])

        ExpenseAuditLog.objects.create(
            expense=expense,
            user=request.user,
            action=ExpenseAuditLog.Action.REJECTED,
            old_value={'status': old_status},
            new_value={
                'status': expense.status,
                'reason': serializer.validated_data.get('note', ''),
            },
            ip_address=get_client_ip(request),
        )
        return Response(
            {'message': 'Expense rejected.', 'expense': ExpenseSerializer(expense, context={'request': request}).data},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'], url_path='mark_paid')
    def mark_paid(self, request, pk=None):
        """Mark an expense as paid."""
        expense = self.get_object()
        if expense.status != Expense.Status.APPROVED:
            return Response(
                {'error': 'Expense must be approved before marking as paid.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        paid_date_str = request.data.get('paid_date')
        if paid_date_str:
            from dateutil.parser import parse as parse_date
            try:
                expense.paid_date = parse_date(paid_date_str).date()
            except Exception:
                expense.paid_date = date.today()
        else:
            expense.paid_date = date.today()

        expense.status = Expense.Status.PAID
        expense.save(update_fields=['status', 'paid_date', 'updated_at'])

        ExpenseAuditLog.objects.create(
            expense=expense,
            user=request.user,
            action=ExpenseAuditLog.Action.PAID,
            new_value={'paid_date': str(expense.paid_date)},
            ip_address=get_client_ip(request),
        )
        return Response(
            {'message': 'Expense marked as paid.', 'paid_date': str(expense.paid_date)},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'], url_path='allocate')
    def allocate(self, request, pk=None):
        """Trigger or re-trigger allocation for this expense."""
        expense = self.get_object()
        year = request.data.get('year', expense.expense_date.year)
        try:
            year = int(year)
        except (ValueError, TypeError):
            year = expense.expense_date.year

        allocations = ExpenseAllocationService.allocate_expense(expense, year)

        ExpenseAuditLog.objects.create(
            expense=expense,
            user=request.user,
            action=ExpenseAuditLog.Action.ALLOCATED,
            new_value={
                'year': year,
                'method': expense.allocation_method,
                'count': len(allocations),
            },
            ip_address=get_client_ip(request),
        )

        return Response({
            'message': f'Expense allocated using {expense.allocation_method}.',
            'allocations': ExpenseAllocationSerializer(
                allocations, many=True, context={'request': request}
            ).data,
        })

    @action(detail=False, methods=['post'], url_path='bulk_create')
    def bulk_create(self, request):
        """Create multiple expenses at once."""
        expenses_data = request.data.get('expenses', [])
        if not isinstance(expenses_data, list) or not expenses_data:
            return Response(
                {'error': 'Provide a list of expenses under the "expenses" key.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created_expenses = []
        errors = []

        for i, expense_data in enumerate(expenses_data):
            serializer = ExpenseSerializer(data=expense_data, context={'request': request})
            if serializer.is_valid():
                expense = serializer.save(created_by=request.user)
                ExpenseAuditLog.objects.create(
                    expense=expense,
                    user=request.user,
                    action=ExpenseAuditLog.Action.BULK_UPLOADED,
                    new_value={'index': i, 'title': expense.title},
                    ip_address=get_client_ip(request),
                )
                try:
                    ExpenseAllocationService.allocate_expense(expense)
                except Exception as e:
                    logger.warning(f"Bulk allocation failed for {expense.unique_id}: {e}")
                created_expenses.append(expense)
            else:
                errors.append({'index': i, 'errors': serializer.errors})

        return Response({
            'created_count': len(created_expenses),
            'error_count': len(errors),
            'created': ExpenseSerializer(created_expenses, many=True, context={'request': request}).data,
            'errors': errors,
        }, status=status.HTTP_201_CREATED if created_expenses else status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request):
        """Return expense summary for a year."""
        from django.db.models import Sum, Count
        import calendar

        year = request.query_params.get('year')
        try:
            year = int(year) if year else date.today().year
        except ValueError:
            year = date.today().year

        qs = Expense.objects.filter(expense_date__year=year)

        total_amount = qs.aggregate(total=Sum('amount'))['total'] or 0
        by_status = qs.values('status').annotate(count=Count('id'), total=Sum('amount'))
        by_category = qs.values('category').annotate(count=Count('id'), total=Sum('amount'))
        by_method = qs.values('allocation_method').annotate(count=Count('id'), total=Sum('amount'))

        return Response({
            'year': year,
            'total_amount': str(total_amount),
            'total_count': qs.count(),
            'by_status': list(by_status),
            'by_category': list(by_category),
            'by_allocation_method': list(by_method),
        })


class ExpenseOCRView(APIView):
    """
    Trigger OCR processing for an expense receipt.
    POST /expenses/{id}/ocr/

    Currently returns mock extracted data. In production this would call
    a real OCR service (e.g., AWS Textract, Google Vision, or a Swiss-specific service).
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk=None):
        try:
            expense = Expense.objects.get(pk=pk)
        except Expense.DoesNotExist:
            return Response(
                {'error': 'Expense not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not expense.receipt_file:
            return Response(
                {'error': 'No receipt file attached to this expense.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Mock OCR processing - in production, call actual OCR service
        mock_extracted = {
            'vendor_name': expense.vendor_name or 'Mock Vendor AG',
            'amount': str(expense.amount),
            'currency': expense.currency,
            'expense_date': str(expense.expense_date),
            'is_qr_bill': expense.is_qr_bill,
            'qr_reference': expense.qr_reference or '',
            'qr_creditor_iban': expense.qr_creditor_iban or '',
            'raw_text': (
                f"RECHNUNG\n"
                f"Vendor: {expense.vendor_name or 'Mock Vendor AG'}\n"
                f"Betrag: CHF {expense.amount}\n"
                f"Datum: {expense.expense_date}\n"
                f"Referenz: {expense.payment_reference or 'N/A'}\n"
            ),
            'confidence_score': round(random.uniform(0.75, 0.98), 4),
        }

        expense.ocr_extracted_data = mock_extracted
        expense.ocr_raw_data = {
            'provider': 'mock',
            'processed_at': str(date.today()),
            'file_name': expense.receipt_file.name,
        }
        expense.ocr_confidence_score = mock_extracted['confidence_score']
        expense.is_ocr_reviewed = False
        expense.save(update_fields=[
            'ocr_extracted_data', 'ocr_raw_data',
            'ocr_confidence_score', 'is_ocr_reviewed', 'updated_at',
        ])

        ExpenseAuditLog.objects.create(
            expense=expense,
            user=request.user,
            action=ExpenseAuditLog.Action.OCR_PROCESSED,
            new_value={
                'confidence_score': mock_extracted['confidence_score'],
                'provider': 'mock',
            },
            ip_address=get_client_ip(request),
        )

        serializer = OCRResultSerializer(mock_extracted)
        return Response({
            'message': 'OCR processing completed.',
            'extracted_data': serializer.data,
            'expense_id': expense.id,
            'unique_id': expense.unique_id,
        })


class ExpenseAllocationView(APIView):
    """
    GET /expenses/{id}/allocations/ - get all allocations for an expense
    POST /expenses/{id}/allocations/ - recalculate allocations
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk=None):
        try:
            expense = Expense.objects.get(pk=pk)
        except Expense.DoesNotExist:
            return Response({'error': 'Expense not found.'}, status=status.HTTP_404_NOT_FOUND)

        allocations = expense.allocations.select_related('manager').all()
        serializer = ExpenseAllocationSerializer(allocations, many=True, context={'request': request})
        return Response({
            'expense_id': expense.id,
            'unique_id': expense.unique_id,
            'allocation_method': expense.allocation_method,
            'total_amount': str(expense.amount),
            'allocations': serializer.data,
        })

    def post(self, request, pk=None):
        """Recalculate allocations for this expense."""
        try:
            expense = Expense.objects.get(pk=pk)
        except Expense.DoesNotExist:
            return Response({'error': 'Expense not found.'}, status=status.HTTP_404_NOT_FOUND)

        year = request.data.get('year', expense.expense_date.year)
        try:
            year = int(year)
        except (ValueError, TypeError):
            year = expense.expense_date.year

        allocations = ExpenseAllocationService.allocate_expense(expense, year)
        serializer = ExpenseAllocationSerializer(allocations, many=True, context={'request': request})
        return Response({
            'message': 'Allocations recalculated.',
            'allocations': serializer.data,
        })
