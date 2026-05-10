"""
Accounting views: AccountingEntry CRUD, FiscalYear management, Dashboard
"""
import logging
from datetime import date

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from .models import AccountingEntry, FiscalYear
from .serializers import (
    AccountingEntrySerializer, FiscalYearSerializer,
    YearEndCloseSerializer, DashboardDataSerializer,
)
from .services import YearEndService, RevenueService

logger = logging.getLogger(__name__)


class FiscalYearViewSet(ModelViewSet):
    """
    Manage fiscal years.

    GET    /accounting/fiscal-years/                - list
    POST   /accounting/fiscal-years/                - create
    GET    /accounting/fiscal-years/{id}/           - retrieve
    PATCH  /accounting/fiscal-years/{id}/           - update notes
    POST   /accounting/fiscal-years/{id}/close/     - year-end close
    GET    /accounting/fiscal-years/{id}/settlement/ - settlement report
    """
    serializer_class = FiscalYearSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['year', 'status']
    ordering = ['-year']
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_queryset(self):
        return FiscalYear.objects.select_related('closed_by').all()

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=True, methods=['post'], url_path='close')
    def close(self, request, pk=None):
        """Execute year-end closing for this fiscal year."""
        fiscal_year = self.get_object()
        serializer = YearEndCloseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if serializer.validated_data['year'] != fiscal_year.year:
            return Response(
                {'error': 'Year in request body does not match this fiscal year.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            closed_fy = YearEndService.close_year(fiscal_year.year, request.user)
            if serializer.validated_data.get('notes'):
                closed_fy.notes = serializer.validated_data['notes']
                closed_fy.save(update_fields=['notes'])
            return Response({
                'message': f'Fiscal year {fiscal_year.year} successfully closed.',
                'fiscal_year': FiscalYearSerializer(closed_fy, context={'request': request}).data,
            })
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Year-end close error: {e}")
            return Response(
                {'error': 'Year-end closing failed. See server logs.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=['get'], url_path='settlement')
    def settlement(self, request, pk=None):
        """Generate settlement report for this fiscal year."""
        fiscal_year = self.get_object()
        try:
            report = YearEndService.generate_settlement_report(fiscal_year.year)
            return Response(report)
        except Exception as e:
            logger.error(f"Settlement report error for {fiscal_year.year}: {e}")
            return Response(
                {'error': f'Failed to generate report: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AccountingEntryViewSet(ModelViewSet):
    """
    CRUD for accounting entries.

    GET    /accounting/entries/          - list
    POST   /accounting/entries/          - create
    GET    /accounting/entries/{id}/     - retrieve
    PATCH  /accounting/entries/{id}/     - update (only open entries)
    DELETE /accounting/entries/{id}/     - delete (only open entries)
    """
    serializer_class = AccountingEntrySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['entry_type', 'is_closed', 'currency', 'manager', 'fiscal_year']
    search_fields = ['description', 'unique_id', 'reference']
    ordering_fields = ['date', 'amount', 'created_at', 'entry_type']
    ordering = ['-date']

    def get_queryset(self):
        qs = AccountingEntry.objects.select_related(
            'manager', 'created_by', 'fiscal_year', 'expense', 'payroll_period'
        )
        year = self.request.query_params.get('year')
        if year:
            try:
                qs = qs.filter(date__year=int(year))
            except ValueError:
                pass
        return qs

    def perform_create(self, serializer):
        year = serializer.validated_data.get('date', date.today()).year
        fiscal_year = FiscalYear.get_or_create_current()
        if fiscal_year.year != year:
            from apps.accounting.models import FiscalYear as FY
            fiscal_year, _ = FY.objects.get_or_create(
                year=year, defaults={'status': FY.Status.OPEN}
            )
        if fiscal_year.is_closed:
            from rest_framework import serializers as rf_serializers
            raise rf_serializers.ValidationError(
                f'Fiscal year {year} is closed. Cannot add new entries.'
            )
        serializer.save(created_by=self.request.user, fiscal_year=fiscal_year)

    def update(self, request, *args, **kwargs):
        entry = self.get_object()
        if entry.is_closed:
            return Response(
                {'error': 'This entry is closed and cannot be modified.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        entry = self.get_object()
        if entry.is_closed:
            return Response(
                {'error': 'This entry is closed and cannot be deleted.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)


class DashboardView(APIView):
    """
    GET /accounting/dashboard/?year=2026
    Returns all KPIs for the main dashboard.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        year = request.query_params.get('year', date.today().year)
        try:
            year = int(year)
        except (ValueError, TypeError):
            return Response({'error': 'Invalid year.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            data = RevenueService.get_dashboard_data(year)
            return Response(data)
        except Exception as e:
            logger.error(f"Dashboard data error for {year}: {e}")
            return Response(
                {'error': f'Failed to load dashboard: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class SettlementReportView(APIView):
    """
    GET /accounting/settlement/?year=2026
    Generates comprehensive settlement report.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        year = request.query_params.get('year', date.today().year)
        try:
            year = int(year)
        except (ValueError, TypeError):
            return Response({'error': 'Invalid year.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            report = YearEndService.generate_settlement_report(year)
            return Response(report)
        except Exception as e:
            logger.error(f"Settlement report error for {year}: {e}")
            return Response(
                {'error': f'Failed to generate report: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
