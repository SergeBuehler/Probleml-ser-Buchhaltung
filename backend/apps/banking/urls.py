"""
Banking URL configuration.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'accounts', views.BankAccountViewSet, basename='bankaccount')
router.register(r'transactions', views.BankTransactionViewSet, basename='banktransaction')

urlpatterns = [
    path('reconciliation/', views.ReconciliationView.as_view(), name='reconciliation-list'),
    path('reconciliation/accept/', views.ReconciliationAcceptView.as_view(), name='reconciliation-accept'),
    path('reconciliation/reject/', views.ReconciliationRejectView.as_view(), name='reconciliation-reject'),
    path('sync/', views.SyncView.as_view(), name='bank-sync'),
    path('', include(router.urls)),
]
