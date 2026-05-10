"""
Properties serializers: Property, PropertyDocument, PropertyHistory
"""
from rest_framework import serializers
from django.utils import timezone

from apps.accounts.serializers import UserSerializer
from .models import Property, PropertyDocument, PropertyHistory


class PropertyDocumentSerializer(serializers.ModelSerializer):
    """Serializer for PropertyDocument."""
    uploaded_by_detail = UserSerializer(source='uploaded_by', read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = PropertyDocument
        fields = [
            'id', 'property', 'file', 'file_url', 'document_type',
            'description', 'uploaded_by', 'uploaded_by_detail', 'uploaded_at',
        ]
        read_only_fields = ['id', 'uploaded_at', 'uploaded_by']

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None


class PropertyHistorySerializer(serializers.ModelSerializer):
    """Serializer for PropertyHistory."""
    changed_by_detail = UserSerializer(source='changed_by', read_only=True)

    class Meta:
        model = PropertyHistory
        fields = [
            'id', 'property', 'change_type', 'old_value', 'new_value',
            'changed_by', 'changed_by_detail', 'changed_at', 'notes',
        ]
        read_only_fields = ['id', 'changed_at']


class PropertySerializer(serializers.ModelSerializer):
    """Serializer for Property model."""
    assigned_manager_detail = UserSerializer(source='assigned_manager', read_only=True)
    document_count = serializers.SerializerMethodField()
    is_first_year = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = [
            'id', 'unique_id', 'name', 'address', 'description',
            'assigned_manager', 'assigned_manager_detail',
            'annual_management_fee', 'management_start_date', 'management_end_date',
            'is_active', 'notes', 'created_at', 'updated_at',
            'document_count', 'is_first_year',
        ]
        read_only_fields = ['id', 'unique_id', 'created_at', 'updated_at']

    def get_document_count(self, obj):
        return obj.documents.count()

    def get_is_first_year(self, obj):
        return obj.management_start_date.year == timezone.now().year

    def validate_management_end_date(self, value):
        if value is not None:
            start_date = self.initial_data.get('management_start_date')
            if start_date and str(value) < str(start_date):
                raise serializers.ValidationError(
                    'Management end date cannot be before start date.'
                )
        return value

    def validate_annual_management_fee(self, value):
        if value <= 0:
            raise serializers.ValidationError('Annual management fee must be positive.')
        return value


class PropertyDetailSerializer(PropertySerializer):
    """Detailed serializer including documents and history."""
    documents = PropertyDocumentSerializer(many=True, read_only=True)
    history = PropertyHistorySerializer(many=True, read_only=True)

    class Meta(PropertySerializer.Meta):
        fields = PropertySerializer.Meta.fields + ['documents', 'history']


class PropertyRevenueSerializer(serializers.Serializer):
    """Serializer for property revenue calculation response."""
    property_id = serializers.IntegerField()
    property_unique_id = serializers.CharField()
    property_name = serializers.CharField()
    year = serializers.IntegerField()
    annual_fee = serializers.DecimalField(max_digits=12, decimal_places=2)
    prorated_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    monthly_breakdown = serializers.DictField(
        child=serializers.DecimalField(max_digits=12, decimal_places=2)
    )


class ManagerRevenueSerializer(serializers.Serializer):
    """Serializer for manager revenue summary."""
    manager_id = serializers.IntegerField()
    manager_name = serializers.CharField()
    revenue = serializers.DecimalField(max_digits=14, decimal_places=2)
    property_count = serializers.IntegerField()
    percentage = serializers.DecimalField(max_digits=7, decimal_places=4)


class AllRevenueSerializer(serializers.Serializer):
    """Serializer for all-manager revenue response."""
    year = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=14, decimal_places=2)
    managers = ManagerRevenueSerializer(many=True)
