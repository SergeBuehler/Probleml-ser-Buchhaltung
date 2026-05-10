"""
Payroll URL configuration.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'employees', views.EmployeeViewSet, basename='employee')
router.register(r'periods', views.PayrollPeriodViewSet, basename='payrollperiod')
router.register(r'certificates', views.SalaryCertificateViewSet, basename='salarycertificate')

urlpatterns = [
    path('calculate/', views.CalculatePayrollView.as_view(), name='payroll-calculate'),
    path('summary/', views.PayrollSummaryView.as_view(), name='payroll-summary'),
    path('', include(router.urls)),
]
