"""
Properties views: full CRUD for Property, PropertyDocument, PropertyHistory,
plus revenue calculation endpoints.
"""
import logging
from decimal import Decimal

from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from .models import Property, PropertyDocument, PropertyHistory
from .serializers import (
    PropertySerializer, PropertyDetailSerializer,
    PropertyDocumentSerializer, PropertyHistorySerializer,
    AllRevenueSerializer,
)
from .services import (
    calculate_all_revenue, calculate_manager_revenue,
    calculate_prorated_revenue, get_property_revenue_breakdown,
)

logger = logging.getLogger(__name__)


class PropertyViewSet(ModelViewSet):
    """
    CRUD endpoints for properties.
    GET    /properties/           - list
    POST   /properties/           - create
    GET    /properties/{id}/      - retrieve
    PUT    /properties/{id}/      - update
    PATCH  /properties/{id}/      - partial update
    DELETE /properties/{id}/      - deactivate (soft delete)
    GET    /properties/{id}/revenue/ - revenue for a year
    GET    /properties/revenue_summary/ - all-manager revenue summary
    """
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['assigned_manager', 'is_active', 'management_start_date']
    search_fields = ['name', 'address', 'unique_id']
    ordering_fields = ['name', 'created_at', 'annual_management_fee', 'management_start_date']
    ordering = ['name']

    def get_queryset(self):
        return Property.objects.select_related(
            'assigned_manager', 'created_by'
        ).prefetch_related('documents')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return PropertyDetailSerializer
        return PropertySerializer

    def perform_create(self, serializer):
        prop = serializer.save(created_by=self.request.user)
        PropertyHistory.objects.create(
            property=prop,
            change_type=PropertyHistory.ChangeType.CREATED,
            new_value={
                'name': prop.name,
                'annual_management_fee': str(prop.annual_management_fee),
                'management_start_date': str(prop.management_start_date),
                'assigned_manager_id': prop.assigned_manager_id,
            },
            changed_by=self.request.user,
        )
        logger.info(f"Property created: {prop.unique_id} by {self.request.user.email}")

    def perform_update(self, serializer):
        old_prop = self.get_object()
        old_data = {
            'name': old_prop.name,
            'annual_management_fee': str(old_prop.annual_management_fee),
            'assigned_manager_id': old_prop.assigned_manager_id,
            'is_active': old_prop.is_active,
        }
        prop = serializer.save()
        new_data = {
            'name': prop.name,
            'annual_management_fee': str(prop.annual_management_fee),
            'assigned_manager_id': prop.assigned_manager_id,
            'is_active': prop.is_active,
        }
        # Determine change type
        if old_data['annual_management_fee'] != new_data['annual_management_fee']:
            change_type = PropertyHistory.ChangeType.FEE_CHANGED
        elif old_data['assigned_manager_id'] != new_data['assigned_manager_id']:
            change_type = PropertyHistory.ChangeType.MANAGER_CHANGED
        elif not prop.is_active and old_data['is_active']:
            change_type = PropertyHistory.ChangeType.DEACTIVATED
        elif prop.is_active and not old_data['is_active']:
            change_type = PropertyHistory.ChangeType.REACTIVATED
        else:
            change_type = PropertyHistory.ChangeType.UPDATED

        PropertyHistory.objects.create(
            property=prop,
            change_type=change_type,
            old_value=old_data,
            new_value=new_data,
            changed_by=self.request.user,
        )
        logger.info(f"Property updated: {prop.unique_id} by {self.request.user.email}")

    def destroy(self, request, *args, **kwargs):
        """Soft-delete: deactivate property instead of removing from DB."""
        prop = self.get_object()
        prop.is_active = False
        prop.management_end_date = timezone.now().date()
        prop.save()
        PropertyHistory.objects.create(
            property=prop,
            change_type=PropertyHistory.ChangeType.DEACTIVATED,
            old_value={'is_active': True},
            new_value={'is_active': False},
            changed_by=request.user,
        )
        logger.info(f"Property deactivated: {prop.unique_id} by {request.user.email}")
        return Response(
            {'message': f'Property {prop.unique_id} deactivated.'},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['get'], url_path='revenue')
    def revenue(self, request, pk=None):
        """Get revenue breakdown for this property for a given year."""
        prop = self.get_object()
        year = request.query_params.get('year', timezone.now().year)
        try:
            year = int(year)
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid year parameter.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        breakdown = get_property_revenue_breakdown(prop, year)
        prorated = calculate_prorated_revenue(
            annual_fee=prop.annual_management_fee,
            start_date=prop.management_start_date,
            year=year,
            end_date=prop.management_end_date,
        )
        breakdown['prorated_revenue'] = prorated
        # Convert Decimal keys to strings for JSON serialization
        breakdown['monthly_breakdown'] = {
            str(k): str(v) for k, v in breakdown['monthly_breakdown'].items()
        }
        return Response(breakdown)

    @action(detail=False, methods=['get'], url_path='revenue_summary')
    def revenue_summary(self, request):
        """Get revenue summary for all managers for a given year."""
        year = request.query_params.get('year', timezone.now().year)
        try:
            year = int(year)
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid year parameter.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = calculate_all_revenue(year)

        # Build response list for managers
        managers_list = []
        for manager_id, info in data['managers'].items():
            managers_list.append({
                'manager_id': info['manager_id'],
                'manager_name': info['manager_name'],
                'revenue': str(info['revenue']),
                'property_count': info['property_count'],
                'percentage': str(data['percentages'].get(manager_id, Decimal('0'))),
            })

        return Response({
            'year': year,
            'total_revenue': str(data['total_revenue']),
            'managers': managers_list,
            'percentages': {str(k): str(v) for k, v in data['percentages'].items()},
        })


class PropertyDocumentViewSet(ModelViewSet):
    """CRUD for property documents."""
    serializer_class = PropertyDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        return PropertyDocument.objects.select_related(
            'property', 'uploaded_by'
        ).filter(property__isnull=False)

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)


class PropertyDocumentListView(generics.ListCreateAPIView):
    """List and upload documents for a specific property."""
    serializer_class = PropertyDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        return PropertyDocument.objects.filter(
            property_id=self.kwargs['property_pk']
        ).select_related('uploaded_by')

    def perform_create(self, serializer):
        property_obj = generics.get_object_or_404(Property, pk=self.kwargs['property_pk'])
        serializer.save(uploaded_by=self.request.user, property=property_obj)


class PropertyHistoryListView(generics.ListAPIView):
    """List audit history for a specific property."""
    serializer_class = PropertyHistorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PropertyHistory.objects.filter(
            property_id=self.kwargs['property_pk']
        ).select_related('changed_by').order_by('-changed_at')


class RevenueView(APIView):
    """
    Revenue calculation endpoint.
    GET /properties/revenue/?year=2026
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        year = request.query_params.get('year', timezone.now().year)
        try:
            year = int(year)
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid year parameter.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = calculate_all_revenue(year)

        managers_list = []
        for manager_id, info in data['managers'].items():
            managers_list.append({
                'manager_id': info['manager_id'],
                'manager_name': info['manager_name'],
                'revenue': str(info['revenue']),
                'property_count': info['property_count'],
                'percentage': str(data['percentages'].get(manager_id, Decimal('0'))),
            })

        return Response({
            'year': year,
            'total_revenue': str(data['total_revenue']),
            'managers': managers_list,
            'percentages': {str(k): str(v) for k, v in data['percentages'].items()},
        })
