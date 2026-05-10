"""
Expense allocation service.
Handles MANAGER_A, MANAGER_B, FIFTY_FIFTY, and REVENUE_BASED allocation methods.
"""
import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import List

logger = logging.getLogger(__name__)


def get_managers():
    """Return the two property managers ordered by ID (A = lower ID, B = higher ID)."""
    from apps.accounts.models import CustomUser
    managers = list(
        CustomUser.objects.filter(
            role=CustomUser.Role.MANAGER, is_active=True
        ).order_by('id')
    )
    return managers


class ExpenseAllocationService:
    """
    Service to allocate expenses between managers.

    Manager A = first manager (lower ID)
    Manager B = second manager (higher ID)
    """

    @staticmethod
    def allocate_expense(expense, year: int = None) -> List:
        """
        Allocate an expense and return a list of ExpenseAllocation objects.
        Creates or updates allocations in the database.

        Args:
            expense: Expense model instance
            year: fiscal year for revenue-based allocation (defaults to expense_date.year)

        Returns:
            List of ExpenseAllocation instances
        """
        from apps.expenses.models import ExpenseAllocation

        if year is None:
            year = expense.expense_date.year

        managers = get_managers()
        if not managers:
            logger.warning(f"No managers found for expense {expense.unique_id} allocation.")
            return []

        # Delete existing allocations
        ExpenseAllocation.objects.filter(expense=expense).delete()

        allocations = []

        if expense.allocation_method == 'MANAGER_A':
            if len(managers) >= 1:
                allocations = ExpenseAllocationService._allocate_single(
                    expense, managers[0], Decimal('100'), expense.amount
                )
            else:
                logger.error("MANAGER_A allocation: no managers found.")

        elif expense.allocation_method == 'MANAGER_B':
            if len(managers) >= 2:
                allocations = ExpenseAllocationService._allocate_single(
                    expense, managers[1], Decimal('100'), expense.amount
                )
            elif len(managers) == 1:
                # Fallback: only one manager exists
                allocations = ExpenseAllocationService._allocate_single(
                    expense, managers[0], Decimal('100'), expense.amount
                )
                logger.warning("MANAGER_B allocation: only one manager found, assigning to them.")
            else:
                logger.error("MANAGER_B allocation: no managers found.")

        elif expense.allocation_method == 'FIFTY_FIFTY':
            allocations = ExpenseAllocationService._allocate_fifty_fifty(expense, managers)

        elif expense.allocation_method == 'REVENUE_BASED':
            allocations = ExpenseAllocationService._allocate_revenue_based(expense, managers, year)

        else:
            logger.warning(
                f"Unknown allocation method '{expense.allocation_method}' "
                f"for expense {expense.unique_id}. Defaulting to 50/50."
            )
            allocations = ExpenseAllocationService._allocate_fifty_fifty(expense, managers)

        logger.info(
            f"Allocated expense {expense.unique_id} "
            f"({expense.allocation_method}): {len(allocations)} allocations created."
        )
        return allocations

    @staticmethod
    def _allocate_single(expense, manager, percentage: Decimal, amount: Decimal) -> List:
        """Allocate 100% to a single manager."""
        from apps.expenses.models import ExpenseAllocation

        alloc = ExpenseAllocation.objects.create(
            expense=expense,
            manager=manager,
            amount=amount,
            percentage=percentage,
            allocation_type=ExpenseAllocation.AllocationType.FIXED,
        )
        return [alloc]

    @staticmethod
    def _allocate_fifty_fifty(expense, managers: list) -> List:
        """Split expense 50/50 between two managers."""
        from apps.expenses.models import ExpenseAllocation

        if len(managers) < 2:
            if managers:
                return ExpenseAllocationService._allocate_single(
                    expense, managers[0], Decimal('100'), expense.amount
                )
            return []

        amount = Decimal(str(expense.amount))
        half = (amount / Decimal('2')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        # Handle rounding: give remainder to manager A
        remainder = amount - (half * 2)
        amount_a = half + remainder
        amount_b = half

        allocs = []
        alloc_a = ExpenseAllocation.objects.create(
            expense=expense,
            manager=managers[0],
            amount=amount_a,
            percentage=Decimal('50.0000'),
            allocation_type=ExpenseAllocation.AllocationType.PERCENTAGE,
        )
        alloc_b = ExpenseAllocation.objects.create(
            expense=expense,
            manager=managers[1],
            amount=amount_b,
            percentage=Decimal('50.0000'),
            allocation_type=ExpenseAllocation.AllocationType.PERCENTAGE,
        )
        allocs = [alloc_a, alloc_b]
        return allocs

    @staticmethod
    def _allocate_revenue_based(expense, managers: list, year: int) -> List:
        """
        Allocate proportionally to each manager's revenue share in the given year.
        """
        from apps.expenses.models import ExpenseAllocation
        from apps.properties.services import calculate_all_revenue

        revenue_data = calculate_all_revenue(year)
        percentages = revenue_data.get('percentages', {})
        total_revenue = revenue_data.get('total_revenue', Decimal('0'))

        if total_revenue == Decimal('0') or not percentages:
            # Fallback to 50/50 if no revenue data
            logger.warning(
                f"No revenue data for year {year}. Falling back to 50/50 for "
                f"expense {expense.unique_id}."
            )
            return ExpenseAllocationService._allocate_fifty_fifty(expense, managers)

        amount = Decimal(str(expense.amount))
        allocs = []
        total_allocated = Decimal('0.00')

        for i, manager in enumerate(managers):
            pct = percentages.get(manager.id, Decimal('0'))
            if i == len(managers) - 1:
                # Last manager gets the remainder to avoid rounding errors
                manager_amount = amount - total_allocated
            else:
                manager_amount = (amount * pct / Decimal('100')).quantize(
                    Decimal('0.01'), rounding=ROUND_HALF_UP
                )
            total_allocated += manager_amount

            alloc = ExpenseAllocation.objects.create(
                expense=expense,
                manager=manager,
                amount=manager_amount,
                percentage=pct,
                allocation_type=ExpenseAllocation.AllocationType.REVENUE,
            )
            allocs.append(alloc)

        return allocs

    @staticmethod
    def recalculate_all_for_year(year: int) -> int:
        """
        Recalculate all REVENUE_BASED expense allocations for a given year.
        Called when revenue changes (e.g., property added/removed).

        Returns:
            Number of expenses recalculated.
        """
        from apps.expenses.models import Expense

        revenue_expenses = Expense.objects.filter(
            allocation_method='REVENUE_BASED',
            expense_date__year=year,
        )
        count = 0
        for expense in revenue_expenses:
            try:
                ExpenseAllocationService.allocate_expense(expense, year)
                count += 1
            except Exception as e:
                logger.error(
                    f"Failed to recalculate allocation for expense {expense.unique_id}: {e}"
                )

        logger.info(f"Recalculated {count} revenue-based expense allocations for year {year}.")
        return count

    @staticmethod
    def get_manager_total_expenses(manager, year: int) -> Decimal:
        """Get total expense amount allocated to a manager for a given year."""
        from apps.expenses.models import ExpenseAllocation

        result = ExpenseAllocation.objects.filter(
            manager=manager,
            expense__expense_date__year=year,
            expense__status__in=['APPROVED', 'PAID'],
        ).aggregate(
            total=models.Sum('amount')
        )
        from django.db import models as dj_models
        total = ExpenseAllocation.objects.filter(
            manager=manager,
            expense__expense_date__year=year,
            expense__status__in=['APPROVED', 'PAID'],
        ).aggregate(total=dj_models.Sum('amount'))['total']
        return Decimal(str(total or '0')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def get_client_ip(request) -> str:
    """Extract client IP from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')
