"""
Accounting serializers: AccountingEntry, FiscalYear
"""
from rest_framework import serializers
from apps.accounts.serializers import UserSerializer
from .models import AccountingEntry, FiscalYear


class FiscalYearSerializer(serializers.ModelSerializer):
    """Serializer for FiscalYear."""
    closed_by_detail = UserSerializer(source='closed_by', read_only=True)
    status_display = serializers.ReadOnlyField(source='get_status_display')
    total_revenue = serializers.SerializerMethodField()
    net_result = serializers.SerializerMethodField()

    class Meta:
        model = FiscalYear
        fields = [
            'id', 'year', 'status', 'status_display',
            'closed_at', 'closed_by', 'closed_by_detail',
            'revenue_percentages_snapshot',
            'total_revenue_a', 'total_revenue_b', 'total_revenue',
            'total_expenses', 'total_payroll', 'net_result',
            'notes', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'closed_at', 'closed_by', 'revenue_percentages_snapshot',
            'total_revenue_a', 'total_revenue_b', 'total_expenses', 'total_payroll',
            'created_at', 'updated_at',
        ]

    def get_total_revenue(self, obj):
        from decimal import Decimal
        return str(
            Decimal(str(obj.total_revenue_a or 0)) + Decimal(str(obj.total_revenue_b or 0))
        )

    def get_net_result(self, obj):
        from decimal import Decimal
        total_revenue = Decimal(str(obj.total_revenue_a or 0)) + Decimal(str(obj.total_revenue_b or 0))
        total_costs = Decimal(str(obj.total_expenses or 0)) + Decimal(str(obj.total_payroll or 0))
        return str(total_revenue - total_costs)


class AccountingEntrySerializer(serializers.ModelSerializer):
    """Serializer for AccountingEntry."""
    created_by_detail = UserSerializer(source='created_by', read_only=True)
    manager_detail = UserSerializer(source='manager', read_only=True)
    entry_type_display = serializers.ReadOnlyField(source='get_entry_type_display')
    fiscal_year_year = serializers.ReadOnlyField(source='fiscal_year.year')

    class Meta:
        model = AccountingEntry
        fields = [
            'id', 'unique_id', 'entry_type', 'entry_type_display',
            'description', 'amount', 'currency', 'date',
            'fiscal_year', 'fiscal_year_year',
            'manager', 'manager_detail',
            'expense', 'payroll_period',
            'is_closed', 'reference', 'notes',
            'created_by', 'created_by_detail',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'unique_id', 'is_closed', 'created_at', 'updated_at']

    def validate(self, attrs):
        # Prevent editing closed entries
        instance = self.instance
        if instance and instance.is_closed:
            raise serializers.ValidationError('This accounting entry is closed and cannot be modified.')
        return attrs


class YearEndCloseSerializer(serializers.Serializer):
    """Serializer for year-end closing request."""
    year = serializers.IntegerField()
    confirmation = serializers.CharField(
        help_text='Must be "CONFIRM_CLOSE_{year}" to proceed.'
    )
    notes = serializers.CharField(required=False, allow_blank=True, default='')

    def validate(self, attrs):
        year = attrs.get('year')
        confirmation = attrs.get('confirmation', '')
        expected = f'CONFIRM_CLOSE_{year}'
        if confirmation != expected:
            raise serializers.ValidationError({
                'confirmation': f'Must be exactly "{expected}" to close year {year}.'
            })
        return attrs


class DashboardDataSerializer(serializers.Serializer):
    """Serializer for dashboard KPI response."""
    year = serializers.IntegerField()
    revenue = serializers.DictField()
    expenses = serializers.DictField()
    properties = serializers.DictField()
    payroll = serializers.DictField()
    banking = serializers.DictField()
