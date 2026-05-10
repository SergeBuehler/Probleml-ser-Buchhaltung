"""
Properties URL configuration.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'', views.PropertyViewSet, basename='property')

urlpatterns = [
    path('revenue/', views.RevenueView.as_view(), name='revenue-summary'),
    path('<int:property_pk>/documents/', views.PropertyDocumentListView.as_view(), name='property-documents'),
    path('<int:property_pk>/history/', views.PropertyHistoryListView.as_view(), name='property-history'),
    path('', include(router.urls)),
]
