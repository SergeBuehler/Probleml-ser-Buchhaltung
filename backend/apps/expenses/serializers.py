"""
Expenses serializers: Expense, ExpenseAllocation, ExpenseAuditLog
"""
from rest_framework import serializers
from apps.accounts.serializers import UserSerializer
from .models import Expense, ExpenseAllocation, ExpenseAuditLog


class ExpenseAllocationSerializer(serializers.ModelSerializer):
    """Serializer for ExpenseAllocation."""
    manager_detail = UserSerializer(source='manager', read_only=True)

    class Meta:
        model = ExpenseAllocation
        fields = [
            'id', 'expense', 'manager', 'manager_detail',
            'amount', 'percentage', 'allocation_type', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class ExpenseAuditLogSerializer(serializers.ModelSerializer):
    """Serializer for ExpenseAuditLog."""
    user_detail = UserSerializer(source='user', read_only=True)

    class Meta:
        model = ExpenseAuditLog
        fields = [
            'id', 'expense', 'user', 'user_detail', 'action',
            'old_value', 'new_value', 'timestamp', 'ip_address', 'notes',
        ]
        read_only_fields = ['id', 'timestamp']


class ExpenseSerializer(serializers.ModelSerializer):
    """Serializer for Expense model."""
    created_by_detail = UserSerializer(source='created_by', read_only=True)
    receipt_file_url = serializers.SerializerMethodField()
    allocation_count = serializers.SerializerMethodField()

    class Meta:
        model = Expense
        fields = [
            'id', 'unique_id', 'title', 'description',
            'amount', 'currency', 'vat_amount', 'net_amount',
            'expense_date', 'due_date', 'paid_date',
            'category', 'allocation_method', 'allocation_note', 'status',
            'created_by', 'created_by_detail',
            'vendor_name', 'vendor_iban', 'payment_reference',
            'receipt_file', 'receipt_file_url',
            'is_qr_bill', 'qr_reference', 'qr_creditor_iban',
            'ocr_raw_data', 'ocr_extracted_data', 'ocr_confidence_score', 'is_ocr_reviewed',
            'created_at', 'updated_at',
            'allocation_count',
        ]
        read_only_fields = [
            'id', 'unique_id', 'created_at', 'updated_at', 'created_by',
        ]
        extra_kwargs = {
            'receipt_file': {'write_only': True},
            'ocr_raw_data': {'read_only': True},
        }

    def get_receipt_file_url(self, obj):
        request = self.context.get('request')
        if obj.receipt_file and request:
            return request.build_absolute_uri(obj.receipt_file.url)
        return None

    def get_allocation_count(self, obj):
        return obj.allocations.count()

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Amount must be positive.')
        return value

    def validate(self, attrs):
        paid_date = attrs.get('paid_date')
        expense_date = attrs.get('expense_date')
        if paid_date and expense_date and paid_date < expense_date:
            raise serializers.ValidationError({
                'paid_date': 'Paid date cannot be before expense date.'
            })
        return attrs


class ExpenseDetailSerializer(ExpenseSerializer):
    """Detailed serializer including allocations and audit logs."""
    allocations = ExpenseAllocationSerializer(many=True, read_only=True)
    audit_logs = ExpenseAuditLogSerializer(many=True, read_only=True)

    class Meta(ExpenseSerializer.Meta):
        fields = ExpenseSerializer.Meta.fields + ['allocations', 'audit_logs']


class ExpenseBulkCreateSerializer(serializers.Serializer):
    """Serializer for bulk expense creation."""
    expenses = ExpenseSerializer(many=True)

    def create(self, validated_data):
        expenses_data = validated_data.pop('expenses')
        created = []
        for expense_data in expenses_data:
            expense = Expense.objects.create(**expense_data)
            created.append(expense)
        return created


class ExpenseStatusUpdateSerializer(serializers.Serializer):
    """Serializer for approving/rejecting expenses."""
    status = serializers.ChoiceField(choices=Expense.Status.choices)
    note = serializers.CharField(required=False, allow_blank=True, default='')


class OCRResultSerializer(serializers.Serializer):
    """Serializer for OCR extraction results."""
    vendor_name = serializers.CharField(allow_blank=True, default='')
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    currency = serializers.CharField(default='CHF')
    expense_date = serializers.DateField(required=False)
    is_qr_bill = serializers.BooleanField(default=False)
    qr_reference = serializers.CharField(allow_blank=True, default='')
    qr_creditor_iban = serializers.CharField(allow_blank=True, default='')
    confidence_score = serializers.FloatField(default=0.0)
    raw_text = serializers.CharField(allow_blank=True, default='')
