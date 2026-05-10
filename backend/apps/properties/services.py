"""
Properties revenue calculation service.
Handles prorated revenue for first year, full year for subsequent years,
and partial year if management ended mid-year.
"""
import logging
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

logger = logging.getLogger(__name__)


def calculate_prorated_revenue(
    annual_fee: Decimal,
    start_date: date,
    year: int,
    end_date: Optional[date] = None,
) -> Decimal:
    """
    Calculate prorated revenue for a given year.

    Rules:
    - If start_date.year == year: prorate from start month to end of year (or end_date)
      formula: (annual_fee / 12) * (12 - start_date.month + 1)
    - If start_date.year < year and property is active for the full year: annual_fee
    - If property ended mid-year (end_date.year == year): prorate to end month
    - If property was not active in the given year: Decimal('0')
    """
    annual_fee = Decimal(str(annual_fee))
    monthly_fee = (annual_fee / Decimal('12')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    # Property hadn't started yet
    if start_date.year > year:
        return Decimal('0.00')

    # Property ended before this year
    if end_date is not None and end_date.year < year:
        return Decimal('0.00')

    # Determine the active months in the given year
    if start_date.year == year:
        start_month = start_date.month
    else:
        start_month = 1

    if end_date is not None and end_date.year == year:
        end_month = end_date.month
    else:
        end_month = 12

    active_months = end_month - start_month + 1

    if active_months <= 0:
        return Decimal('0.00')

    if active_months == 12:
        return annual_fee

    revenue = (monthly_fee * Decimal(str(active_months))).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP
    )
    return revenue


def calculate_manager_revenue(manager, year: int) -> Decimal:
    """
    Calculate total revenue for a single manager in a given year.
    Sums prorated revenue for all their properties active in that year.
    """
    from apps.properties.models import Property

    properties = Property.objects.filter(assigned_manager=manager)
    total = Decimal('0.00')

    for prop in properties:
        revenue = calculate_prorated_revenue(
            annual_fee=prop.annual_management_fee,
            start_date=prop.management_start_date,
            year=year,
            end_date=prop.management_end_date,
        )
        total += revenue
        logger.debug(
            f"Property {prop.unique_id} ({prop.name}) – year {year} revenue: {revenue}"
        )

    return total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def calculate_all_revenue(year: int) -> dict:
    """
    Calculate revenue for all managers in a given year.

    Returns:
        {
            'year': year,
            'managers': {
                manager_id: {
                    'manager_id': int,
                    'manager_name': str,
                    'revenue': Decimal,
                    'property_count': int,
                }
            },
            'total_revenue': Decimal,
            'percentages': {
                manager_id: Decimal  (0-100)
            }
        }
    """
    from apps.accounts.models import CustomUser

    managers = CustomUser.objects.filter(
        role=CustomUser.Role.MANAGER, is_active=True
    )

    manager_revenues = {}
    total_revenue = Decimal('0.00')

    for manager in managers:
        revenue = calculate_manager_revenue(manager, year)
        from apps.properties.models import Property
        prop_count = Property.objects.filter(assigned_manager=manager).count()
        manager_revenues[manager.id] = {
            'manager_id': manager.id,
            'manager_name': manager.full_name,
            'revenue': revenue,
            'property_count': prop_count,
        }
        total_revenue += revenue

    percentages = {}
    for manager_id, data in manager_revenues.items():
        if total_revenue > Decimal('0'):
            pct = (data['revenue'] / total_revenue * Decimal('100')).quantize(
                Decimal('0.0001'), rounding=ROUND_HALF_UP
            )
        else:
            count = len(manager_revenues)
            pct = (Decimal('100') / Decimal(str(count))).quantize(
                Decimal('0.0001'), rounding=ROUND_HALF_UP
            ) if count > 0 else Decimal('0')
        percentages[manager_id] = pct

    return {
        'year': year,
        'managers': manager_revenues,
        'total_revenue': total_revenue.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
        'percentages': percentages,
    }


def calculate_monthly_revenue(manager, year: int, month: int) -> Decimal:
    """
    Calculate revenue for a specific manager in a specific month.
    A property contributes monthly_fee if it was active in that month.
    """
    from apps.properties.models import Property

    properties = Property.objects.filter(assigned_manager=manager)
    total = Decimal('0.00')
    month_date = date(year, month, 1)

    for prop in properties:
        start = prop.management_start_date
        end = prop.management_end_date

        # Check if property was active in this month
        if start > date(year, month, 28 if month in [2] else 30 if month in [4, 6, 9, 11] else 31):
            continue
        if end is not None and end < month_date:
            continue

        monthly_fee = (
            Decimal(str(prop.annual_management_fee)) / Decimal('12')
        ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        total += monthly_fee

    return total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def get_property_revenue_breakdown(property_obj, year: int) -> dict:
    """
    Get a detailed month-by-month revenue breakdown for a single property.
    """
    from calendar import monthrange

    monthly_fee = (
        Decimal(str(property_obj.annual_management_fee)) / Decimal('12')
    ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    breakdown = {}
    total = Decimal('0.00')

    for month in range(1, 13):
        last_day = monthrange(year, month)[1]
        month_start = date(year, month, 1)
        month_end = date(year, month, last_day)

        start = property_obj.management_start_date
        end = property_obj.management_end_date

        # Property not yet started
        if start > month_end:
            breakdown[month] = Decimal('0.00')
            continue

        # Property already ended
        if end is not None and end < month_start:
            breakdown[month] = Decimal('0.00')
            continue

        breakdown[month] = monthly_fee
        total += monthly_fee

    return {
        'property_id': property_obj.id,
        'property_unique_id': property_obj.unique_id,
        'property_name': property_obj.name,
        'year': year,
        'annual_fee': property_obj.annual_management_fee,
        'monthly_breakdown': breakdown,
        'total_year_revenue': total,
    }
