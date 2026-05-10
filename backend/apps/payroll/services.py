"""
Swiss payroll calculation service.
Implements AHV, IV, EO, ALV, NBU, BVG contributions per 2024 Swiss rates.
"""
import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

logger = logging.getLogger(__name__)


def round_chf(value: Decimal, decimals: int = 2) -> Decimal:
    """Round to Swiss Rappen (0.05 CHF precision for wages, 0.01 for calculations)."""
    quantize_str = '0.' + '0' * decimals
    return value.quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP)


class SwissPayrollCalculator:
    """
    Swiss payroll calculator applying 2024 rates.

    Social insurance rates (combined employee + employer where applicable):
    - AHV (Alters- und Hinterlassenenversicherung): 8.7% total (4.35% each)
      Note: Using spec rates:
      AHV employee = 5.3% (includes AHV 4.35% + solidarity contrib)
      AHV employer = 5.3%
    - IV (Invalidenversicherung): 1.4% total (0.7% each)
    - EO (Erwerbsersatzordnung): 0.5% total (0.25% each)
    - ALV (Arbeitslosenversicherung): 2.2% total (1.1% each)
    - NBU (Nichtberufsunfallversicherung): employee only, ~0.17% (varies by insurer)
    - BVG (Berufliche Vorsorge): varies by age/plan; using 7% employee, 7% employer as example
    - KTG (Krankentaggeld): 1.2% total (0.6% each)
    """

    # Employee contribution rates
    AHV_RATE_EMPLOYEE = Decimal('0.0535')   # 5.35% (AHV 4.35% + solidarity 0.5% + admin 0.2% example)
    IV_RATE_EMPLOYEE = Decimal('0.007')     # 0.7%
    EO_RATE_EMPLOYEE = Decimal('0.0025')    # 0.25%
    ALV_RATE_EMPLOYEE = Decimal('0.011')    # 1.1%
    NBU_RATE = Decimal('0.0017')            # 0.17% (varies by insurer)
    BVG_RATE_EMPLOYEE = Decimal('0.07')     # 7% (varies by age tier)
    KTG_RATE_EMPLOYEE = Decimal('0.006')    # 0.6% (varies by plan)

    # Employer contribution rates (mirror employee for AHV/IV/EO/ALV)
    AHV_RATE_EMPLOYER = Decimal('0.0535')
    IV_RATE_EMPLOYER = Decimal('0.007')
    EO_RATE_EMPLOYER = Decimal('0.0025')
    ALV_RATE_EMPLOYER = Decimal('0.011')
    NBU_RATE_EMPLOYER = Decimal('0.0034')   # employer share of BU (occupational accident)
    BVG_RATE_EMPLOYER = Decimal('0.07')     # 7% employer contribution
    KTG_RATE_EMPLOYER = Decimal('0.006')    # 0.6%

    # ALV max insured salary (2024: CHF 148,200 / year = 12,350/month)
    ALV_MAX_MONTHLY = Decimal('12350.00')

    # AHV exemption for owners/employers (Freibetrag): CHF 1,400/month in some cantons
    OWNER_AHV_EXEMPTION_MONTHLY = Decimal('0.00')  # 0 = no exemption by default

    @classmethod
    def calculate_period(
        cls,
        employee,
        year: int,
        month: int,
        gross_salary: Optional[Decimal] = None,
        vacation_days: int = 25,
        include_bvg: bool = True,
        bvg_employee_rate: Optional[Decimal] = None,
        bvg_employer_rate: Optional[Decimal] = None,
    ):
        """
        Calculate payroll for one month.

        Args:
            employee: Employee model instance
            year: payroll year
            month: payroll month (1-12)
            gross_salary: override gross salary (uses employee.gross_salary if None)
            vacation_days: annual vacation days (default 25)
            include_bvg: whether to include BVG contributions
            bvg_employee_rate: override BVG employee rate
            bvg_employer_rate: override BVG employer rate

        Returns:
            PayrollPeriod instance (saved to database)
        """
        from apps.payroll.models import PayrollPeriod

        if gross_salary is None:
            gross_salary = Decimal(str(employee.gross_salary))
        else:
            gross_salary = Decimal(str(gross_salary))

        bvg_emp_rate = bvg_employee_rate or cls.BVG_RATE_EMPLOYEE
        bvg_er_rate = bvg_employer_rate or cls.BVG_RATE_EMPLOYER

        # AHV/IV/EO base = gross salary
        ahv_base = gross_salary
        alv_base = min(gross_salary, cls.ALV_MAX_MONTHLY)

        # Employee deductions
        ahv_employee = round_chf(ahv_base * cls.AHV_RATE_EMPLOYEE)
        iv_employee = round_chf(ahv_base * cls.IV_RATE_EMPLOYEE)
        eo_employee = round_chf(ahv_base * cls.EO_RATE_EMPLOYEE)
        alv_employee = round_chf(alv_base * cls.ALV_RATE_EMPLOYEE)
        nbu_employee = round_chf(gross_salary * cls.NBU_RATE)
        bvg_employee = round_chf(gross_salary * bvg_emp_rate) if include_bvg else Decimal('0.00')
        ktg_employee = round_chf(gross_salary * cls.KTG_RATE_EMPLOYEE)

        total_deductions = (
            ahv_employee + iv_employee + eo_employee + alv_employee
            + nbu_employee + bvg_employee + ktg_employee
        )
        net_salary = round_chf(gross_salary - total_deductions)

        # Employer contributions
        ahv_employer = round_chf(ahv_base * cls.AHV_RATE_EMPLOYER)
        iv_employer = round_chf(ahv_base * cls.IV_RATE_EMPLOYER)
        eo_employer = round_chf(ahv_base * cls.EO_RATE_EMPLOYER)
        alv_employer = round_chf(alv_base * cls.ALV_RATE_EMPLOYER)
        nbu_employer = round_chf(gross_salary * cls.NBU_RATE_EMPLOYER)
        bvg_employer = round_chf(gross_salary * bvg_er_rate) if include_bvg else Decimal('0.00')
        ktg_employer = round_chf(gross_salary * cls.KTG_RATE_EMPLOYER)

        total_employer_cost = round_chf(
            gross_salary
            + ahv_employer + iv_employer + eo_employer + alv_employer
            + nbu_employer + bvg_employer + ktg_employer
        )

        # Accruals
        # Vacation accrual: approximation based on 220 working days/year
        vacation_accrual = round_chf(
            gross_salary / Decimal('12') * Decimal(str(vacation_days)) / Decimal('220')
        )
        thirteenth_salary_accrual = round_chf(gross_salary / Decimal('12'))

        # Create or update PayrollPeriod
        period, created = PayrollPeriod.objects.update_or_create(
            employee=employee,
            year=year,
            month=month,
            defaults={
                'gross_salary': gross_salary,
                'ahv_employee': ahv_employee,
                'iv_employee': iv_employee,
                'eo_employee': eo_employee,
                'alv_employee': alv_employee,
                'nbu_employee': nbu_employee,
                'bvg_employee': bvg_employee,
                'ktg_employee': ktg_employee,
                'total_deductions_employee': total_deductions,
                'net_salary': net_salary,
                'ahv_employer': ahv_employer,
                'iv_employer': iv_employer,
                'eo_employer': eo_employer,
                'alv_employer': alv_employer,
                'nbu_employer': nbu_employer,
                'bvg_employer': bvg_employer,
                'ktg_employer': ktg_employer,
                'total_employer_cost': total_employer_cost,
                'vacation_accrual': vacation_accrual,
                'thirteenth_salary_accrual': thirteenth_salary_accrual,
                'status': PayrollPeriod.PeriodStatus.DRAFT,
            }
        )

        logger.info(
            f"Payroll period {'created' if created else 'updated'}: "
            f"{employee.full_name} {year}/{month:02d} – "
            f"Gross: {gross_salary}, Net: {net_salary}"
        )
        return period

    @classmethod
    def calculate_yearly_certificate(cls, employee, year: int):
        """
        Generate or update annual salary certificate from all finalized payroll periods.

        Args:
            employee: Employee instance
            year: year to generate certificate for

        Returns:
            SalaryCertificate instance
        """
        from apps.payroll.models import PayrollPeriod, SalaryCertificate
        from django.db.models import Sum

        periods = PayrollPeriod.objects.filter(
            employee=employee,
            year=year,
            status__in=[PayrollPeriod.PeriodStatus.FINAL, PayrollPeriod.PeriodStatus.PAID],
        )

        aggregates = periods.aggregate(
            total_gross=Sum('gross_salary'),
            total_net=Sum('net_salary'),
            total_ahv=Sum('ahv_employee'),
            total_alv=Sum('alv_employee'),
            total_bvg=Sum('bvg_employee'),
            total_nbu=Sum('nbu_employee'),
            total_13th=Sum('thirteenth_salary_accrual'),
        )

        gross_year = Decimal(str(aggregates['total_gross'] or '0'))
        net_year = Decimal(str(aggregates['total_net'] or '0'))
        ahv_total = Decimal(str(aggregates['total_ahv'] or '0'))
        alv_total = Decimal(str(aggregates['total_alv'] or '0'))
        bvg_total = Decimal(str(aggregates['total_bvg'] or '0'))
        nbu_total = Decimal(str(aggregates['total_nbu'] or '0'))
        thirteenth = Decimal(str(aggregates['total_13th'] or '0'))

        cert, created = SalaryCertificate.objects.update_or_create(
            employee=employee,
            year=year,
            defaults={
                'gross_salary_year': round_chf(gross_year),
                'net_salary_year': round_chf(net_year),
                'ahv_total': round_chf(ahv_total),
                'alv_total': round_chf(alv_total),
                'bvg_total': round_chf(bvg_total),
                'nbu_total': round_chf(nbu_total),
                'thirteenth_salary': round_chf(thirteenth),
                'status': SalaryCertificate.CertificateStatus.DRAFT,
            }
        )

        logger.info(
            f"Salary certificate {'created' if created else 'updated'}: "
            f"{employee.full_name} {year} – Gross: {gross_year}"
        )
        return cert

    @classmethod
    def calculate_all_employees_for_month(cls, year: int, month: int) -> list:
        """
        Calculate payroll for all active employees for a given month.

        Returns:
            List of PayrollPeriod instances.
        """
        from apps.payroll.models import Employee

        employees = Employee.objects.filter(
            is_active=True,
            employment_start_date__lte=f'{year}-{month:02d}-28',
        ).filter(
            models.Q(employment_end_date__isnull=True) |
            models.Q(employment_end_date__gte=f'{year}-{month:02d}-01')
        )

        from django.db import models as dj_models
        employees = Employee.objects.filter(
            is_active=True,
        ).filter(
            dj_models.Q(employment_end_date__isnull=True) |
            dj_models.Q(employment_end_date__year__gte=year)
        )

        periods = []
        for employee in employees:
            try:
                period = cls.calculate_period(employee, year, month)
                periods.append(period)
            except Exception as e:
                logger.error(
                    f"Payroll calculation failed for {employee.full_name} "
                    f"{year}/{month:02d}: {e}"
                )

        logger.info(
            f"Batch payroll for {year}/{month:02d}: "
            f"{len(periods)} employees processed."
        )
        return periods

    @classmethod
    def get_payroll_summary(cls, year: int) -> dict:
        """
        Return yearly payroll summary across all employees.
        """
        from apps.payroll.models import PayrollPeriod
        from django.db.models import Sum, Count

        qs = PayrollPeriod.objects.filter(year=year)
        agg = qs.aggregate(
            total_gross=Sum('gross_salary'),
            total_net=Sum('net_salary'),
            total_ahv_employee=Sum('ahv_employee'),
            total_alv_employee=Sum('alv_employee'),
            total_bvg_employee=Sum('bvg_employee'),
            total_employer_cost=Sum('total_employer_cost'),
            total_vacation_accrual=Sum('vacation_accrual'),
            total_thirteenth=Sum('thirteenth_salary_accrual'),
            period_count=Count('id'),
        )

        return {
            'year': year,
            'period_count': agg['period_count'] or 0,
            'total_gross': str(agg['total_gross'] or 0),
            'total_net': str(agg['total_net'] or 0),
            'total_ahv_employee': str(agg['total_ahv_employee'] or 0),
            'total_alv_employee': str(agg['total_alv_employee'] or 0),
            'total_bvg_employee': str(agg['total_bvg_employee'] or 0),
            'total_employer_cost': str(agg['total_employer_cost'] or 0),
            'total_vacation_accrual': str(agg['total_vacation_accrual'] or 0),
            'total_thirteenth_accrual': str(agg['total_thirteenth'] or 0),
        }
