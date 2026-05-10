"""
Accounting services: YearEndService, RevenueService
"""
import logging
from decimal import Decimal, ROUND_HALF_UP
from datetime import date

from django.utils import timezone

logger = logging.getLogger(__name__)


class YearEndService:
    """
    Handles fiscal year-end closing procedure.

    Steps:
    1. Snapshot revenue percentages
    2. Finalize all expense allocations
    3. Create accounting summary entries
    4. Lock the fiscal year
    """

    @classmethod
    def close_year(cls, year: int, user) -> 'FiscalYear':
        """
        Execute year-end closing for the given year.

        Args:
            year: fiscal year to close
            user: user performing the closing

        Returns:
            FiscalYear instance with CLOSED status
        """
        from apps.accounting.models import FiscalYear, AccountingEntry
        from apps.expenses.models import Expense
        from apps.payroll.models import PayrollPeriod
        from apps.properties.services import calculate_all_revenue
        from apps.expenses.services import ExpenseAllocationService

        fiscal_year, _ = FiscalYear.objects.get_or_create(
            year=year, defaults={'status': FiscalYear.Status.OPEN}
        )

        if fiscal_year.status == FiscalYear.Status.CLOSED:
            raise ValueError(f"Fiscal year {year} is already closed.")

        # Mark as closing in progress
        fiscal_year.status = FiscalYear.Status.CLOSING
        fiscal_year.save(update_fields=['status', 'updated_at'])

        try:
            # Step 1: Snapshot revenue percentages
            revenue_data = calculate_all_revenue(year)
            fiscal_year.revenue_percentages_snapshot = {
                'year': year,
                'total_revenue': str(revenue_data['total_revenue']),
                'managers': {
                    str(k): {
                        'manager_id': v['manager_id'],
                        'manager_name': v['manager_name'],
                        'revenue': str(v['revenue']),
                        'property_count': v['property_count'],
                    }
                    for k, v in revenue_data['managers'].items()
                },
                'percentages': {
                    str(k): str(v)
                    for k, v in revenue_data['percentages'].items()
                },
                'snapshotted_at': timezone.now().isoformat(),
            }

            # Determine manager A and B revenues
            manager_revenues = sorted(
                revenue_data['managers'].values(),
                key=lambda x: x['manager_id']
            )
            if len(manager_revenues) >= 1:
                fiscal_year.total_revenue_a = manager_revenues[0]['revenue']
            if len(manager_revenues) >= 2:
                fiscal_year.total_revenue_b = manager_revenues[1]['revenue']

            # Step 2: Recalculate all revenue-based expense allocations
            recalc_count = ExpenseAllocationService.recalculate_all_for_year(year)
            logger.info(f"Year-end {year}: recalculated {recalc_count} expense allocations.")

            # Step 3: Compute totals
            from django.db.models import Sum

            expenses_total = Expense.objects.filter(
                expense_date__year=year,
                status__in=['APPROVED', 'PAID'],
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

            payroll_total = PayrollPeriod.objects.filter(
                year=year,
                status__in=['FINAL', 'PAID'],
            ).aggregate(total=Sum('total_employer_cost'))['total'] or Decimal('0')

            fiscal_year.total_expenses = Decimal(str(expenses_total))
            fiscal_year.total_payroll = Decimal(str(payroll_total))

            # Step 4: Lock all entries for this year
            AccountingEntry.objects.filter(
                date__year=year
            ).update(is_closed=True)

            # Step 5: Close the year
            fiscal_year.status = FiscalYear.Status.CLOSED
            fiscal_year.closed_at = timezone.now()
            fiscal_year.closed_by = user
            fiscal_year.save()

            logger.info(
                f"Fiscal year {year} closed by {user.email}. "
                f"Revenue A: {fiscal_year.total_revenue_a}, "
                f"Revenue B: {fiscal_year.total_revenue_b}, "
                f"Total expenses: {fiscal_year.total_expenses}"
            )

        except Exception as e:
            # Rollback closing status
            fiscal_year.status = FiscalYear.Status.OPEN
            fiscal_year.save(update_fields=['status', 'updated_at'])
            logger.error(f"Year-end closing failed for {year}: {e}")
            raise

        return fiscal_year

    @classmethod
    def generate_settlement_report(cls, year: int) -> dict:
        """
        Generate a comprehensive year-end settlement report.

        Returns:
            dict with full financial breakdown
        """
        from apps.accounting.models import FiscalYear
        from apps.properties.services import calculate_all_revenue
        from apps.expenses.models import Expense, ExpenseAllocation
        from apps.payroll.models import PayrollPeriod
        from apps.accounts.models import CustomUser
        from django.db.models import Sum

        # Get or compute revenue data
        try:
            fiscal_year = FiscalYear.objects.get(year=year)
            if fiscal_year.revenue_percentages_snapshot:
                revenue_snapshot = fiscal_year.revenue_percentages_snapshot
            else:
                revenue_data = calculate_all_revenue(year)
                revenue_snapshot = None
        except FiscalYear.DoesNotExist:
            fiscal_year = None
            revenue_data = calculate_all_revenue(year)
            revenue_snapshot = None

        if not revenue_snapshot:
            revenue_data = calculate_all_revenue(year)
        else:
            revenue_data = calculate_all_revenue(year)

        # Expense breakdown by manager
        managers = CustomUser.objects.filter(
            role=CustomUser.Role.MANAGER, is_active=True
        ).order_by('id')

        manager_expense_breakdown = []
        for manager in managers:
            allocated = ExpenseAllocation.objects.filter(
                manager=manager,
                expense__expense_date__year=year,
                expense__status__in=['APPROVED', 'PAID'],
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

            manager_expense_breakdown.append({
                'manager_id': manager.id,
                'manager_name': manager.full_name,
                'allocated_expenses': str(Decimal(str(allocated))),
                'revenue': str(revenue_data['managers'].get(manager.id, {}).get('revenue', Decimal('0'))),
                'revenue_percentage': str(revenue_data['percentages'].get(manager.id, Decimal('0'))),
            })

        # Payroll totals
        payroll_totals = PayrollPeriod.objects.filter(
            year=year,
            status__in=['FINAL', 'PAID'],
        ).aggregate(
            gross=Sum('gross_salary'),
            net=Sum('net_salary'),
            employer_cost=Sum('total_employer_cost'),
            ahv=Sum('ahv_employer'),
            alv=Sum('alv_employer'),
            bvg=Sum('bvg_employer'),
        )

        # Expense totals by category
        expense_by_category = list(
            Expense.objects.filter(
                expense_date__year=year,
                status__in=['APPROVED', 'PAID'],
            ).values('category').annotate(
                count=models_count(),
                total=Sum('amount'),
            ).order_by('-total')
        )

        total_revenue = revenue_data['total_revenue']
        total_expenses = Expense.objects.filter(
            expense_date__year=year,
            status__in=['APPROVED', 'PAID'],
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        return {
            'year': year,
            'report_generated_at': timezone.now().isoformat(),
            'fiscal_year_status': fiscal_year.get_status_display() if fiscal_year else 'OPEN',
            'revenue': {
                'total': str(total_revenue),
                'by_manager': [
                    {
                        'manager_id': mid,
                        'manager_name': mdata['manager_name'],
                        'revenue': str(mdata['revenue']),
                        'percentage': str(revenue_data['percentages'].get(mid, Decimal('0'))),
                        'property_count': mdata['property_count'],
                    }
                    for mid, mdata in revenue_data['managers'].items()
                ],
            },
            'expenses': {
                'total': str(total_expenses),
                'by_manager': manager_expense_breakdown,
                'by_category': expense_by_category,
            },
            'payroll': {
                'total_gross': str(payroll_totals.get('gross') or 0),
                'total_net': str(payroll_totals.get('net') or 0),
                'total_employer_cost': str(payroll_totals.get('employer_cost') or 0),
                'total_ahv_employer': str(payroll_totals.get('ahv') or 0),
                'total_alv_employer': str(payroll_totals.get('alv') or 0),
                'total_bvg_employer': str(payroll_totals.get('bvg') or 0),
            },
            'net_result': {
                'total_income': str(total_revenue),
                'total_costs': str(
                    Decimal(str(total_expenses)) + Decimal(str(payroll_totals.get('employer_cost') or 0))
                ),
                'net': str(
                    total_revenue
                    - Decimal(str(total_expenses))
                    - Decimal(str(payroll_totals.get('employer_cost') or 0))
                ),
            },
        }


def models_count():
    """Helper to get count aggregation."""
    from django.db.models import Count
    return Count('id')


class RevenueService:
    """Service for revenue calculations and dashboard KPIs."""

    @classmethod
    def get_dashboard_data(cls, year: int) -> dict:
        """
        Aggregate all KPIs for the dashboard.

        Returns:
            dict with revenue, expenses, payroll, banking reconciliation stats
        """
        from apps.properties.services import calculate_all_revenue
        from apps.expenses.models import Expense
        from apps.banking.models import BankTransaction, ReconciliationSuggestion
        from apps.payroll.models import PayrollPeriod, Employee
        from apps.properties.models import Property
        from django.db.models import Sum, Count, Q

        # Revenue
        revenue_data = calculate_all_revenue(year)

        # Expenses
        expense_stats = Expense.objects.filter(expense_date__year=year).aggregate(
            total=Sum('amount'),
            count=Count('id'),
            pending=Count('id', filter=Q(status='PENDING')),
            approved=Count('id', filter=Q(status='APPROVED')),
            paid=Count('id', filter=Q(status='PAID')),
            rejected=Count('id', filter=Q(status='REJECTED')),
        )

        # Properties
        property_stats = Property.objects.aggregate(
            total=Count('id'),
            active=Count('id', filter=Q(is_active=True)),
        )

        # Payroll
        payroll_stats = PayrollPeriod.objects.filter(year=year).aggregate(
            total_gross=Sum('gross_salary'),
            total_net=Sum('net_salary'),
            period_count=Count('id'),
        )

        # Banking
        banking_stats = {
            'unreconciled_transactions': BankTransaction.objects.filter(
                status='PENDING', transaction_type='DEBIT'
            ).count(),
            'pending_suggestions': ReconciliationSuggestion.objects.filter(
                status='PENDING'
            ).count(),
        }

        # Employee count
        employee_count = Employee.objects.filter(is_active=True).count()

        return {
            'year': year,
            'revenue': {
                'total': str(revenue_data['total_revenue']),
                'by_manager': [
                    {
                        'manager_id': mid,
                        'manager_name': mdata['manager_name'],
                        'revenue': str(mdata['revenue']),
                        'percentage': str(revenue_data['percentages'].get(mid, Decimal('0'))),
                        'property_count': mdata['property_count'],
                    }
                    for mid, mdata in revenue_data['managers'].items()
                ],
            },
            'expenses': {
                'total': str(expense_stats['total'] or 0),
                'count': expense_stats['count'] or 0,
                'pending': expense_stats['pending'] or 0,
                'approved': expense_stats['approved'] or 0,
                'paid': expense_stats['paid'] or 0,
                'rejected': expense_stats['rejected'] or 0,
            },
            'properties': {
                'total': property_stats['total'] or 0,
                'active': property_stats['active'] or 0,
            },
            'payroll': {
                'total_gross': str(payroll_stats['total_gross'] or 0),
                'total_net': str(payroll_stats['total_net'] or 0),
                'period_count': payroll_stats['period_count'] or 0,
                'employee_count': employee_count,
            },
            'banking': banking_stats,
        }
