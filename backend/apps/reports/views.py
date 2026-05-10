"""
Reports views: generate various reports, CSV/Excel/PDF exports, dashboard
"""
import logging
from datetime import date

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import HttpResponse

from .services import ExcelReportService, PDFReportService, CSVExportService
from apps.accounting.services import RevenueService

logger = logging.getLogger(__name__)


class DashboardView(APIView):
    """
    GET /reports/dashboard/?year=2026
    Returns aggregated dashboard data.
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
            logger.error(f"Dashboard error: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ReportView(APIView):
    """
    Generate various report types.
    GET /reports/?type=annual&year=2026&format=json
    """
    permission_classes = [permissions.IsAuthenticated]

    VALID_TYPES = ['annual', 'revenue', 'expenses', 'payroll', 'settlement', 'reconciliation']
    VALID_FORMATS = ['json', 'excel', 'pdf', 'csv']

    def get(self, request):
        report_type = request.query_params.get('type', 'annual')
        year = request.query_params.get('year', date.today().year)
        fmt = request.query_params.get('format', 'json').lower()

        try:
            year = int(year)
        except (ValueError, TypeError):
            return Response({'error': 'Invalid year.'}, status=status.HTTP_400_BAD_REQUEST)

        if report_type not in self.VALID_TYPES:
            return Response(
                {'error': f'Invalid report type. Choose from: {self.VALID_TYPES}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if fmt not in self.VALID_FORMATS:
            return Response(
                {'error': f'Invalid format. Choose from: {self.VALID_FORMATS}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            if fmt == 'json':
                return self._handle_json(report_type, year, request)
            elif fmt == 'excel':
                return self._handle_excel(report_type, year)
            elif fmt == 'pdf':
                return self._handle_pdf(report_type, year, request)
            elif fmt == 'csv':
                return self._handle_csv(report_type, year, request)
        except Exception as e:
            logger.error(f"Report generation error ({report_type}/{fmt}/{year}): {e}")
            return Response(
                {'error': f'Report generation failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _handle_json(self, report_type: str, year: int, request) -> Response:
        from apps.properties.services import calculate_all_revenue
        from apps.accounting.services import YearEndService

        if report_type in ('annual', 'settlement'):
            data = YearEndService.generate_settlement_report(year)
        elif report_type == 'revenue':
            data = calculate_all_revenue(year)
            # Convert Decimal keys/values to strings
            data['total_revenue'] = str(data['total_revenue'])
            data['managers'] = {
                str(k): {**v, 'revenue': str(v['revenue'])}
                for k, v in data['managers'].items()
            }
            data['percentages'] = {str(k): str(v) for k, v in data['percentages'].items()}
        elif report_type == 'expenses':
            from apps.expenses.models import Expense
            from django.db.models import Sum, Count, Q
            data = {
                'year': year,
                'expenses': list(
                    Expense.objects.filter(expense_date__year=year).values(
                        'unique_id', 'title', 'amount', 'expense_date',
                        'category', 'status', 'allocation_method', 'vendor_name',
                    ).order_by('expense_date')
                ),
                'summary_by_category': list(
                    Expense.objects.filter(expense_date__year=year).values('category').annotate(
                        count=Count('id'), total=Sum('amount')
                    )
                ),
            }
            # Convert Decimal to str
            for exp in data['expenses']:
                exp['amount'] = str(exp['amount'])
                exp['expense_date'] = str(exp['expense_date'])
        elif report_type == 'payroll':
            from apps.payroll.services import SwissPayrollCalculator
            data = SwissPayrollCalculator.get_payroll_summary(year)
        elif report_type == 'reconciliation':
            from apps.banking.models import BankTransaction, ReconciliationSuggestion
            from django.db.models import Count, Q
            data = {
                'year': year,
                'total_transactions': BankTransaction.objects.filter(
                    transaction_date__year=year
                ).count(),
                'reconciled': BankTransaction.objects.filter(
                    transaction_date__year=year, is_reconciled=True
                ).count(),
                'pending': BankTransaction.objects.filter(
                    transaction_date__year=year, status='PENDING'
                ).count(),
                'pending_suggestions': ReconciliationSuggestion.objects.filter(
                    status='PENDING'
                ).count(),
            }

        return Response(data)

    def _handle_excel(self, report_type: str, year: int) -> HttpResponse:
        if report_type == 'expenses':
            content = ExcelReportService.generate_expense_report(year)
            filename = f'expenses_{year}.xlsx'
        else:
            content = ExcelReportService.generate_annual_report(year)
            filename = f'annual_report_{year}.xlsx'

        response = HttpResponse(
            content,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    def _handle_pdf(self, report_type: str, year: int, request) -> HttpResponse:
        if report_type == 'payroll':
            # For a single payslip, require payroll_period_id
            period_id = request.query_params.get('period_id')
            if period_id:
                from apps.payroll.models import PayrollPeriod
                try:
                    period = PayrollPeriod.objects.get(pk=period_id)
                    content = PDFReportService.generate_payslip_pdf(period)
                    filename = f'payslip_{period.employee.last_name}_{year}_{period.month:02d}.pdf'
                except PayrollPeriod.DoesNotExist:
                    return Response({'error': 'PayrollPeriod not found.'}, status=404)
            else:
                content = PDFReportService.generate_annual_summary_pdf(year)
                filename = f'annual_report_{year}.pdf'
        else:
            content = PDFReportService.generate_annual_summary_pdf(year)
            filename = f'annual_report_{year}.pdf'

        response = HttpResponse(content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    def _handle_csv(self, report_type: str, year: int, request) -> HttpResponse:
        manager_id = request.query_params.get('manager_id')

        if report_type == 'expenses':
            content = CSVExportService.export_expenses(year, manager_id)
            filename = f'expenses_{year}.csv'
        elif report_type == 'payroll':
            content = CSVExportService.export_payroll(year)
            filename = f'payroll_{year}.csv'
        elif report_type == 'reconciliation':
            content = CSVExportService.export_transactions(year)
            filename = f'transactions_{year}.csv'
        elif report_type == 'revenue':
            content = CSVExportService.export_revenue(year)
            filename = f'revenue_{year}.csv'
        else:
            content = CSVExportService.export_expenses(year)
            filename = f'report_{year}.csv'

        response = HttpResponse(content, content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class ExportView(APIView):
    """
    Dedicated export endpoint.
    GET /reports/export/?format=excel&type=annual&year=2026
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Delegate to ReportView for exports."""
        return ReportView().get(request)


class PayslipView(APIView):
    """
    Generate payslip PDF for a specific payroll period.
    GET /reports/payslip/{period_id}/
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, period_id):
        from apps.payroll.models import PayrollPeriod
        try:
            period = PayrollPeriod.objects.select_related('employee').get(pk=period_id)
        except PayrollPeriod.DoesNotExist:
            return Response({'error': 'Payroll period not found.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            pdf_content = PDFReportService.generate_payslip_pdf(period)
            filename = (
                f'payslip_{period.employee.last_name}_'
                f'{period.year}_{period.month:02d}.pdf'
            )
            response = HttpResponse(pdf_content, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        except Exception as e:
            logger.error(f"Payslip generation error: {e}")
            return Response(
                {'error': f'Payslip generation failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
