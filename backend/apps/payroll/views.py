"""
Payroll views: Employee CRUD, PayrollPeriod management, SalaryCertificate
"""
import logging
from datetime import date

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from .models import Employee, PayrollPeriod, SalaryCertificate
from .serializers import (
    EmployeeSerializer, PayrollPeriodSerializer,
    SalaryCertificateSerializer, PayrollCalculationRequestSerializer,
    PayrollSummarySerializer,
)
from .services import SwissPayrollCalculator

logger = logging.getLogger(__name__)


class EmployeeViewSet(ModelViewSet):
    """
    CRUD for employees.

    GET    /payroll/employees/           - list
    POST   /payroll/employees/           - create
    GET    /payroll/employees/{id}/      - retrieve
    PUT    /payroll/employees/{id}/      - update
    PATCH  /payroll/employees/{id}/      - partial update
    DELETE /payroll/employees/{id}/      - deactivate
    GET    /payroll/employees/{id}/periods/ - list payroll periods
    GET    /payroll/employees/{id}/certificates/ - list salary certificates
    """
    serializer_class = EmployeeSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'employment_type', 'canton']
    search_fields = ['first_name', 'last_name', 'email', 'ahv_number']
    ordering_fields = ['last_name', 'first_name', 'gross_salary', 'employment_start_date']
    ordering = ['last_name', 'first_name']

    def get_queryset(self):
        return Employee.objects.select_related('user').all()

    def destroy(self, request, *args, **kwargs):
        """Soft delete: deactivate employee."""
        employee = self.get_object()
        employee.is_active = False
        if not employee.employment_end_date:
            employee.employment_end_date = date.today()
        employee.save()
        return Response({'message': f'Employee {employee.full_name} deactivated.'})

    @action(detail=True, methods=['get'], url_path='periods')
    def periods(self, request, pk=None):
        """List all payroll periods for this employee."""
        employee = self.get_object()
        year = request.query_params.get('year')
        qs = employee.payroll_periods.order_by('-year', '-month')
        if year:
            try:
                qs = qs.filter(year=int(year))
            except ValueError:
                pass
        serializer = PayrollPeriodSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='certificates')
    def certificates(self, request, pk=None):
        """List salary certificates for this employee."""
        employee = self.get_object()
        certs = employee.salary_certificates.order_by('-year')
        serializer = SalaryCertificateSerializer(certs, many=True, context={'request': request})
        return Response(serializer.data)


class PayrollPeriodViewSet(ModelViewSet):
    """
    Manage payroll periods.

    GET    /payroll/periods/           - list
    GET    /payroll/periods/{id}/      - retrieve
    POST   /payroll/periods/{id}/finalize/ - finalize period
    DELETE /payroll/periods/{id}/      - delete draft period
    """
    serializer_class = PayrollPeriodSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['year', 'month', 'status', 'employee']
    search_fields = ['employee__first_name', 'employee__last_name']
    ordering_fields = ['year', 'month', 'gross_salary', 'net_salary']
    ordering = ['-year', '-month']
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        return PayrollPeriod.objects.select_related('employee', 'created_by')

    @action(detail=True, methods=['post'], url_path='finalize')
    def finalize(self, request, pk=None):
        """Finalize a draft payroll period."""
        period = self.get_object()
        if period.status != PayrollPeriod.PeriodStatus.DRAFT:
            return Response(
                {'error': f'Period is already {period.status}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        period.status = PayrollPeriod.PeriodStatus.FINAL
        period.save(update_fields=['status', 'updated_at'])
        return Response({
            'message': 'Payroll period finalized.',
            'period': PayrollPeriodSerializer(period, context={'request': request}).data,
        })

    def destroy(self, request, *args, **kwargs):
        """Only allow deletion of DRAFT periods."""
        period = self.get_object()
        if period.status != PayrollPeriod.PeriodStatus.DRAFT:
            return Response(
                {'error': 'Only DRAFT periods can be deleted.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        period.delete()
        return Response({'message': 'Draft period deleted.'})


class CalculatePayrollView(APIView):
    """
    Trigger payroll calculation for one or all employees.
    POST /payroll/calculate/
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PayrollCalculationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        year = serializer.validated_data['year']
        month = serializer.validated_data['month']
        employee_id = serializer.validated_data.get('employee_id')
        gross_override = serializer.validated_data.get('gross_salary_override')
        vacation_days = serializer.validated_data.get('vacation_days', 25)

        if employee_id:
            try:
                employee = Employee.objects.get(pk=employee_id, is_active=True)
            except Employee.DoesNotExist:
                return Response(
                    {'error': f'Employee {employee_id} not found or inactive.'},
                    status=status.HTTP_404_NOT_FOUND,
                )
            period = SwissPayrollCalculator.calculate_period(
                employee=employee,
                year=year,
                month=month,
                gross_salary=gross_override,
                vacation_days=vacation_days,
            )
            period.created_by = request.user
            period.save(update_fields=['created_by'])
            return Response({
                'message': f'Payroll calculated for {employee.full_name}.',
                'period': PayrollPeriodSerializer(period, context={'request': request}).data,
            }, status=status.HTTP_201_CREATED)
        else:
            # Calculate for all active employees
            periods = SwissPayrollCalculator.calculate_all_employees_for_month(year, month)
            return Response({
                'message': f'Payroll calculated for {len(periods)} employees.',
                'year': year,
                'month': month,
                'count': len(periods),
                'periods': PayrollPeriodSerializer(periods, many=True, context={'request': request}).data,
            }, status=status.HTTP_201_CREATED)


class SalaryCertificateViewSet(ModelViewSet):
    """
    Manage salary certificates (Lohnausweis).

    GET    /payroll/certificates/           - list
    GET    /payroll/certificates/{id}/      - retrieve
    POST   /payroll/certificates/generate/  - generate from periods
    POST   /payroll/certificates/{id}/issue/ - issue certificate
    """
    serializer_class = SalaryCertificateSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['year', 'status', 'employee']
    search_fields = ['employee__first_name', 'employee__last_name']
    ordering_fields = ['year', 'gross_salary_year']
    ordering = ['-year']
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_queryset(self):
        return SalaryCertificate.objects.select_related('employee', 'issued_by')

    @action(detail=False, methods=['post'], url_path='generate')
    def generate(self, request):
        """Generate salary certificates for a year."""
        year = request.data.get('year', date.today().year)
        employee_id = request.data.get('employee_id')

        try:
            year = int(year)
        except (ValueError, TypeError):
            return Response({'error': 'Invalid year.'}, status=status.HTTP_400_BAD_REQUEST)

        if employee_id:
            try:
                employees = [Employee.objects.get(pk=employee_id)]
            except Employee.DoesNotExist:
                return Response({'error': 'Employee not found.'}, status=status.HTTP_404_NOT_FOUND)
        else:
            employees = Employee.objects.filter(is_active=True)

        certs = []
        for employee in employees:
            cert = SwissPayrollCalculator.calculate_yearly_certificate(employee, year)
            cert.issued_by = None
            certs.append(cert)

        return Response({
            'message': f'Generated {len(certs)} salary certificate(s) for {year}.',
            'certificates': SalaryCertificateSerializer(certs, many=True, context={'request': request}).data,
        })

    @action(detail=True, methods=['post'], url_path='issue')
    def issue(self, request, pk=None):
        """Issue (finalize) a salary certificate."""
        from django.utils import timezone
        cert = self.get_object()
        if cert.status == SalaryCertificate.CertificateStatus.ISSUED:
            return Response({'error': 'Certificate already issued.'}, status=status.HTTP_400_BAD_REQUEST)
        cert.status = SalaryCertificate.CertificateStatus.ISSUED
        cert.issued_at = timezone.now()
        cert.issued_by = request.user
        cert.save(update_fields=['status', 'issued_at', 'issued_by', 'updated_at'])
        return Response({
            'message': f'Salary certificate for {cert.employee.full_name} {cert.year} issued.',
            'certificate': SalaryCertificateSerializer(cert, context={'request': request}).data,
        })


class PayrollSummaryView(APIView):
    """
    GET /payroll/summary/?year=2026
    Returns aggregated payroll statistics for a year.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        year = request.query_params.get('year', date.today().year)
        try:
            year = int(year)
        except (ValueError, TypeError):
            return Response({'error': 'Invalid year.'}, status=status.HTTP_400_BAD_REQUEST)

        summary = SwissPayrollCalculator.get_payroll_summary(year)
        return Response(summary)
