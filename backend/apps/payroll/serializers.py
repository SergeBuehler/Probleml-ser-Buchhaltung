"""
Payroll serializers: Employee, PayrollPeriod, SalaryCertificate
"""
from rest_framework import serializers
from apps.accounts.serializers import UserSerializer
from .models import Employee, PayrollPeriod, SalaryCertificate


class EmployeeSerializer(serializers.ModelSerializer):
    """Serializer for Employee."""
    user_detail = UserSerializer(source='user', read_only=True)
    full_name = serializers.ReadOnlyField()
    latest_net_salary = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = [
            'id', 'user', 'user_detail', 'first_name', 'last_name', 'full_name',
            'email', 'ahv_number', 'employment_type',
            'employment_start_date', 'employment_end_date',
            'gross_salary', 'bvg_plan', 'accident_insurance',
            'is_active', 'iban', 'address', 'date_of_birth', 'canton',
            'latest_net_salary', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'iban': {'write_only': False},
            'ahv_number': {'write_only': False},
        }

    def get_latest_net_salary(self, obj):
        latest = obj.payroll_periods.filter(
            status__in=['FINAL', 'PAID']
        ).order_by('-year', '-month').first()
        if latest:
            return str(latest.net_salary)
        return None


class PayrollPeriodSerializer(serializers.ModelSerializer):
    """Serializer for PayrollPeriod."""
    employee_detail = serializers.SerializerMethodField()
    month_name = serializers.SerializerMethodField()

    class Meta:
        model = PayrollPeriod
        fields = [
            'id', 'employee', 'employee_detail',
            'year', 'month', 'month_name', 'gross_salary',
            # Employee deductions
            'ahv_employee', 'iv_employee', 'eo_employee',
            'alv_employee', 'nbu_employee', 'bvg_employee', 'ktg_employee',
            'total_deductions_employee', 'net_salary',
            # Employer contributions
            'ahv_employer', 'iv_employer', 'eo_employer',
            'alv_employer', 'nbu_employer', 'bvg_employer', 'ktg_employer',
            'total_employer_cost',
            # Accruals
            'vacation_accrual', 'thirteenth_salary_accrual',
            'status', 'notes', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at',
            'ahv_employee', 'iv_employee', 'eo_employee',
            'alv_employee', 'nbu_employee', 'bvg_employee', 'ktg_employee',
            'total_deductions_employee', 'net_salary',
            'ahv_employer', 'iv_employer', 'eo_employer',
            'alv_employer', 'nbu_employer', 'bvg_employer', 'ktg_employer',
            'total_employer_cost',
            'vacation_accrual', 'thirteenth_salary_accrual',
        ]

    def get_employee_detail(self, obj):
        return {
            'id': obj.employee.id,
            'full_name': obj.employee.full_name,
            'employment_type': obj.employee.employment_type,
        }

    def get_month_name(self, obj):
        import calendar
        return calendar.month_name[obj.month]


class PayrollCalculationRequestSerializer(serializers.Serializer):
    """Request serializer for triggering payroll calculation."""
    year = serializers.IntegerField()
    month = serializers.IntegerField(min_value=1, max_value=12)
    employee_id = serializers.IntegerField(required=False)
    gross_salary_override = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False
    )
    vacation_days = serializers.IntegerField(default=25, min_value=0, max_value=52)


class SalaryCertificateSerializer(serializers.ModelSerializer):
    """Serializer for SalaryCertificate."""
    employee_detail = serializers.SerializerMethodField()
    issued_by_detail = UserSerializer(source='issued_by', read_only=True)

    class Meta:
        model = SalaryCertificate
        fields = [
            'id', 'employee', 'employee_detail', 'year',
            'gross_salary_year', 'ahv_total', 'alv_total', 'bvg_total', 'nbu_total',
            'expense_reimbursements', 'benefits', 'net_salary_year', 'thirteenth_salary',
            'status', 'issued_at', 'issued_by', 'issued_by_detail',
            'notes', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'issued_at',
            'gross_salary_year', 'ahv_total', 'alv_total', 'bvg_total',
            'nbu_total', 'net_salary_year', 'thirteenth_salary',
        ]

    def get_employee_detail(self, obj):
        return {
            'id': obj.employee.id,
            'full_name': obj.employee.full_name,
            'ahv_number': obj.employee.ahv_number,
        }


class PayrollSummarySerializer(serializers.Serializer):
    """Serializer for payroll year summary."""
    year = serializers.IntegerField()
    period_count = serializers.IntegerField()
    total_gross = serializers.CharField()
    total_net = serializers.CharField()
    total_ahv_employee = serializers.CharField()
    total_alv_employee = serializers.CharField()
    total_bvg_employee = serializers.CharField()
    total_employer_cost = serializers.CharField()
    total_vacation_accrual = serializers.CharField()
    total_thirteenth_accrual = serializers.CharField()
