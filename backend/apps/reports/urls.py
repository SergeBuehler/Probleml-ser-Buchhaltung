"""
Reports URL configuration.
"""
from django.urls import path

from . import views

urlpatterns = [
    path('', views.ReportView.as_view(), name='report-generate'),
    path('dashboard/', views.DashboardView.as_view(), name='report-dashboard'),
    path('export/', views.ExportView.as_view(), name='report-export'),
    path('payslip/<int:period_id>/', views.PayslipView.as_view(), name='report-payslip'),
]
