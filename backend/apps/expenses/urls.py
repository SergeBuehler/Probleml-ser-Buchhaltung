"""
Expenses URL configuration.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'', views.ExpenseViewSet, basename='expense')

urlpatterns = [
    path('<int:pk>/ocr/', views.ExpenseOCRView.as_view(), name='expense-ocr'),
    path('<int:pk>/allocations/', views.ExpenseAllocationView.as_view(), name='expense-allocations'),
    path('', include(router.urls)),
]
