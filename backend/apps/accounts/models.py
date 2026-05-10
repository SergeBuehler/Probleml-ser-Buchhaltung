"""
Accounts models: CustomUser, Company, UserCompany
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class CustomUser(AbstractUser):
    """Extended user model with role and contact info."""

    class Role(models.TextChoices):
        MANAGER = 'MANAGER', _('Property Manager')
        ADMIN = 'ADMIN', _('Administrator')
        ACCOUNTANT = 'ACCOUNTANT', _('Accountant')
        VIEWER = 'VIEWER', _('Read-Only Viewer')

    email = models.EmailField(_('email address'), unique=True)
    phone = models.CharField(max_length=30, blank=True, default='')
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MANAGER)
    profile_image = models.ImageField(
        upload_to='profile_images/', null=True, blank=True
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"

    @property
    def full_name(self):
        return self.get_full_name() or self.email

    @property
    def is_manager(self):
        return self.role == self.Role.MANAGER

    @property
    def is_admin_user(self):
        return self.role == self.Role.ADMIN


class Company(models.Model):
    """Represents the property management company."""
    name = models.CharField(max_length=200)
    address = models.TextField(blank=True, default='')
    vat_number = models.CharField(
        max_length=50, blank=True, default='',
        help_text='Swiss VAT number, e.g. CHE-123.456.789 MWST'
    )
    phone = models.CharField(max_length=30, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    website = models.URLField(blank=True, default='')
    logo = models.ImageField(upload_to='company_logos/', null=True, blank=True)
    iban = models.CharField(max_length=34, blank=True, default='')
    bank_name = models.CharField(max_length=100, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Company')
        verbose_name_plural = _('Companies')
        ordering = ['name']

    def __str__(self):
        return self.name


class UserCompany(models.Model):
    """Association between users and companies with roles."""

    class CompanyRole(models.TextChoices):
        OWNER = 'OWNER', _('Owner / Partner')
        MANAGER = 'MANAGER', _('Manager')
        EMPLOYEE = 'EMPLOYEE', _('Employee')
        ACCOUNTANT = 'ACCOUNTANT', _('External Accountant')

    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name='company_memberships'
    )
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name='memberships'
    )
    role = models.CharField(max_length=20, choices=CompanyRole.choices, default=CompanyRole.MANAGER)
    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _('User Company')
        verbose_name_plural = _('User Companies')
        unique_together = ('user', 'company')
        ordering = ['company', 'user']

    def __str__(self):
        return f"{self.user.full_name} @ {self.company.name} ({self.get_role_display()})"
