"""
Accounting REST API Serializers
سيرياليزرز واجهة المحاسبة
"""
from rest_framework import serializers
from django.db.models import Sum
from .models import Account, JournalEntry, JournalEntryItem, CostCenter


class AccountSerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source='parent.name', read_only=True, default=None)
    balance = serializers.SerializerMethodField()

    class Meta:
        model = Account
        fields = [
            'id', 'code', 'name', 'account_type', 'parent', 'parent_name',
            'description', 'is_active', 'can_post', 'is_group', 'level', 'path',
            'requires_cost_center', 'default_cost_center', 'credit_limit',
            'balance', 'created_at', 'updated_at',
        ]
        read_only_fields = ['level', 'path', 'created_at', 'updated_at']

    def get_balance(self, obj):
        try:
            debit = JournalEntryItem.objects.filter(
                account=obj, type='debit', journal_entry__is_posted=True
            ).aggregate(total=Sum('amount'))['total'] or 0
            credit = JournalEntryItem.objects.filter(
                account=obj, type='credit', journal_entry__is_posted=True
            ).aggregate(total=Sum('amount'))['total'] or 0
            return float(debit - credit)
        except Exception:
            return 0.0


class JournalEntryItemSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source='account.name', read_only=True)
    account_code = serializers.CharField(source='account.code', read_only=True)
    debit = serializers.SerializerMethodField()
    credit = serializers.SerializerMethodField()

    class Meta:
        model = JournalEntryItem
        fields = [
            'id', 'account', 'account_name', 'account_code',
            'type', 'amount', 'debit', 'credit', 'description',
            'cost_center', 'reference_document',
        ]

    def get_debit(self, obj):
        return float(obj.amount) if obj.type == 'debit' else 0.0

    def get_credit(self, obj):
        return float(obj.amount) if obj.type == 'credit' else 0.0


class JournalEntryListSerializer(serializers.ModelSerializer):
    """سيرياليزر مُبسّط للقوائم"""
    created_by_name = serializers.CharField(source='created_by.username', read_only=True, default=None)
    total_debit = serializers.SerializerMethodField()

    class Meta:
        model = JournalEntry
        fields = [
            'id', 'number', 'date', 'entry_type', 'description',
            'reference', 'is_posted', 'auto_generated',
            'created_by_name', 'total_debit', 'created_at',
        ]

    def get_total_debit(self, obj):
        return float(obj.items.filter(type='debit').aggregate(
            total=Sum('amount')
        )['total'] or 0)


class JournalEntryDetailSerializer(serializers.ModelSerializer):
    """سيرياليزر مُفصّل مع البنود"""
    items = JournalEntryItemSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True, default=None)

    class Meta:
        model = JournalEntry
        fields = [
            'id', 'number', 'date', 'entry_type', 'description',
            'reference', 'invoice', 'purchase_bill',
            'is_posted', 'auto_generated', 'reversal_of',
            'showroom', 'created_by', 'created_by_name',
            'items', 'created_at', 'updated_at',
        ]
        read_only_fields = ['number', 'created_by', 'created_at', 'updated_at']


class JournalEntryItemCreateSerializer(serializers.Serializer):
    """يقبل شكلين: {type, amount} أو {debit, credit}"""
    account = serializers.PrimaryKeyRelatedField(queryset=Account.objects.all())
    type = serializers.ChoiceField(choices=['debit', 'credit'], required=False)
    amount = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    debit = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, default=0)
    credit = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, default=0)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    cost_center = serializers.PrimaryKeyRelatedField(queryset=CostCenter.objects.all(), required=False, allow_null=True, default=None)
    reference_document = serializers.CharField(required=False, allow_blank=True, default='')

    def validate(self, data):
        # Support both formats: {type, amount} and {debit, credit}
        if data.get('type') and data.get('amount') is not None:
            return data  # native format
        debit_val = data.get('debit', 0) or 0
        credit_val = data.get('credit', 0) or 0
        if debit_val > 0:
            data['type'] = 'debit'
            data['amount'] = debit_val
        elif credit_val > 0:
            data['type'] = 'credit'
            data['amount'] = credit_val
        else:
            if not data.get('type') or data.get('amount') is None:
                raise serializers.ValidationError("يجب تحديد type و amount أو debit/credit")
        data.pop('debit', None)
        data.pop('credit', None)
        return data


class JournalEntryCreateSerializer(serializers.ModelSerializer):
    """سيرياليزر إنشاء قيد مع بنود"""
    items = JournalEntryItemCreateSerializer(many=True)
    date = serializers.DateField(required=False)
    description = serializers.CharField(required=False, allow_blank=True, default='')

    class Meta:
        model = JournalEntry
        fields = [
            'date', 'entry_type', 'description', 'reference',
            'showroom', 'items',
        ]

    def validate(self, data):
        if 'date' not in data or data['date'] is None:
            from datetime import date
            data['date'] = date.today()
        if not data.get('description'):
            data['description'] = 'Journal Entry'
        return data

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("يجب إضافة بند واحد على الأقل")
        total_debit = sum(float(i.get('amount', 0) or 0) for i in value if i.get('type') == 'debit')
        total_credit = sum(float(i.get('amount', 0) or 0) for i in value if i.get('type') == 'credit')
        if abs(total_debit - total_credit) > 0.01:
            raise serializers.ValidationError(
                f"مجموع المدين ({total_debit}) لا يساوي مجموع الدائن ({total_credit})"
            )
        return value

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        entry = JournalEntry.objects.create(
            **validated_data,
            created_by=self.context['request'].user
        )
        for item_data in items_data:
            # Remove extra fields that are not model fields
            item_data.pop('debit', None)
            item_data.pop('credit', None)
            JournalEntryItem.objects.create(journal_entry=entry, **item_data)
        return entry


class CostCenterSerializer(serializers.ModelSerializer):
    class Meta:
        model = CostCenter
        fields = [
            'id', 'code', 'name', 'description',
            'parent', 'manager', 'is_active',
        ]
