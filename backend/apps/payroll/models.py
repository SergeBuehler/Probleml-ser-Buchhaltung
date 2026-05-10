"""
Payroll models: Employee, PayrollPeriod, SalaryCertificate
"""
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Employee(models.Model):
    """Represents an employee for payroll processing."""

    class EmploymentType(models.TextChoices):
        FULL_TIME = 'FULL_TIME', _('Full-Time Employee')
        PART_TIME = 'PART_TIME', _('Part-Time Employee')
        OWNER = 'OWNER', _('Owner / Partner')
        FREELANCE = 'FREELANCE', _('Freelancer')
        APPRENTICE = 'APPRENTICE', _('Apprentice')

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='employee_profile',
        help_text='Linked system user, if applicable.',
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True, default='')
    ahv_number = models.CharField(
        max_length=20, blank=True, default='',
        help_text='Swiss AHV number, e.g. 756.1234.5678.97'
    )
    employment_type = models.CharField(
        max_length=20, choices=EmploymentType.choices, default=EmploymentType.FULL_TIME
    )
    employment_start_date = models.DateField()
    employment_end_date = models.DateField(null=True, blank=True)
    gross_salary = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text='Monthly gross salary in CHF.'
    )
    bvg_plan = models.CharField(
        max_length=200, blank=True, default='',
        help_text='BVG pension plan name or provider.'
    )
    accident_insurance = models.CharField(
        max_length=200, blank=True, default='',
        help_text='Accident insurance plan (NBU/BU).'
    )
    is_active = models.BooleanField(default=True)
    iban = models.CharField(max_length=34, blank=True, default='')
    address = models.TextField(blank=True, default='')
    date_of_birth = models.DateField(null=True, blank=True)
    canton = models.CharField(max_length=2, blank=True, default='ZH',
                              help_text='Swiss canton code for tax purposes.')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Employee')
        verbose_name_plural = _('Employees')
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.last_name}, {self.first_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class PayrollPeriod(models.Model):
    """Monthly payroll calculation for an employee."""

    class PeriodStatus(models.TextChoices):
        DRAFT = 'DRAFT', _('Draft')
        FINAL = 'FINAL', _('Finalized')
        PAID = 'PAID', _('Paid')

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name='payroll_periods'
    )
    year = models.IntegerField()
    month = models.IntegerField()  # 1-12
    gross_salary = models.DecimalField(max_digits=12, decimal_places=2)

    # Employee deductions (employee share)
    ahv_employee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    iv_employee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    eo_employee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    alv_employee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    nbu_employee = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text='Non-occupational accident insurance (NBU) employee share.'
    )
    bvg_employee = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text='BVG pension contribution employee share.'
    )
    ktg_employee = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text='Krankentaggeld (daily sickness benefit) employee share.'
    )
    total_deductions_employee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Employer contributions (employer share)
    ahv_employer = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    iv_employer = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    eo_employer = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    alv_employer = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    nbu_employer = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    bvg_employer = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    ktg_employer = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_employer_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Accruals
    vacation_accrual = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text='Monthly vacation provision (gross/12 * vacation_days/220).'
    )
    thirteenth_salary_accrual = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text='Monthly 13th salary provision (gross/12).'
    )

    status = models.CharField(
        max_length=10, choices=PeriodStatus.choices, default=PeriodStatus.DRAFT
    )
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_payroll_periods',
    )

    class Meta:
        verbose_name = _('Payroll Period')
        verbose_name_plural = _('Payroll Periods')
        unique_together = ('employee', 'year', 'month')
        ordering = ['-year', '-month', 'employee']

    def __str__(self):
        return f"{self.employee.full_name} – {self.year}/{self.month:02d}"


class SalaryCertificate(models.Model):
    """Annual salary certificate (Lohnausweis) for an employee."""

    class CertificateStatus(models.TextChoices):
        DRAFT = 'DRAFT', _('Draft')
        ISSUED = 'ISSUED', _('Issued')

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name='salary_certificates'
    )
    year = models.IntegerField()

    # Yearly totals
    gross_salary_year = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    ahv_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    alv_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    bvg_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    nbu_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    expense_reimbursements = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    benefits = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_salary_year = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    thirteenth_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    status = models.CharField(
        max_length=10, choices=CertificateStatus.choices, default=CertificateStatus.DRAFT
    )
    issued_at = models.DateTimeField(null=True, blank=True)
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='issued_salary_certificates',
    )
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Salary Certificate')
        verbose_name_plural = _('Salary Certificates')
        unique_together = ('employee', 'year')
        ordering = ['-year', 'employee']

    def __str__(self):
        return f"Lohnausweis {self.year} – {self.employee.full_name}"
