"""
Accounting URL configuration.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'fiscal-years', views.FiscalYearViewSet, basename='fiscalyear')
router.register(r'entries', views.AccountingEntryViewSet, basename='accountingentry')

urlpatterns = [
    path('dashboard/', views.DashboardView.as_view(), name='accounting-dashboard'),
    path('settlement/', views.SettlementReportView.as_view(), name='settlement-report'),
    path('', include(router.urls)),
]
