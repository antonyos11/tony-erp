"""
Admin Configuration for Price List System
إعدادات لوحة الإدارة لنظام قوائم الأسعار
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count
from decimal import Decimal

from .models_price_list import (
    ProductSize, ProductFamily, ProductVariant, 
    CostCategory, VariantCostBreakdown, OverheadCostSetting,
    PriceList, ProductVariantPrice, PriceListExport, PriceListSettings
)


# ============ المقاسات ============

@admin.register(ProductSize)
class ProductSizeAdmin(admin.ModelAdmin):
    list_display = ['name', 'width', 'length', 'height', 'price_multiplier', 'cost_multiplier', 'area_display', 'sort_order', 'is_active']
    list_editable = ['price_multiplier', 'cost_multiplier', 'sort_order', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']
    ordering = ['sort_order', 'width', 'length']
    
    fieldsets = (
        ('الأبعاد', {
            'fields': (('width', 'length', 'height'), 'name')
        }),
        ('المعاملات', {
            'fields': (('price_multiplier', 'cost_multiplier'),),
            'description': 'معاملات لحساب السعر والتكلفة تلقائياً بناءً على المقاس'
        }),
        ('العرض', {
            'fields': ('sort_order', 'is_active')
        }),
    )
    
    def area_display(self, obj):
        return f"{obj.area:.2f} م²"
    area_display.short_description = 'المساحة'


# ============ عائلات المنتجات ============

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0
    fields = ['size', 'sku', 'custom_cost', 'calculated_cost', 'is_active']
    readonly_fields = ['calculated_cost']
    autocomplete_fields = ['size']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('size')


@admin.register(ProductFamily)
class ProductFamilyAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'category', 'base_price', 'base_cost', 'sizes_count', 'show_in_price_list', 'is_active']
    list_editable = ['base_price', 'base_cost', 'show_in_price_list', 'is_active']
    list_filter = ['category', 'show_in_price_list', 'is_active']
    search_fields = ['code', 'name', 'name_en']
    ordering = ['sort_order', 'name']
    filter_horizontal = ['available_sizes']
    inlines = [ProductVariantInline]
    
    fieldsets = (
        ('المعلومات الأساسية', {
            'fields': (('code', 'name'), 'name_en', 'description', 'category', 'image')
        }),
        ('التسعير', {
            'fields': (('base_price', 'base_cost'),),
            'description': 'السعر والتكلفة الأساسية لأصغر مقاس'
        }),
        ('المقاسات', {
            'fields': ('available_sizes',),
            'description': 'اختر المقاسات المتاحة لهذه العائلة'
        }),
        ('العرض', {
            'fields': (('sort_order', 'show_in_price_list', 'is_active'),)
        }),
    )
    
    def sizes_count(self, obj):
        return obj.available_sizes.count()
    sizes_count.short_description = 'عدد المقاسات'
    
    actions = ['generate_variants', 'update_prices', 'sync_all_variants_to_inventory']
    
    def generate_variants(self, request, queryset):
        """إنشاء نسخ لكل المقاسات"""
        created = 0
        for family in queryset:
            for size in family.available_sizes.all():
                variant, was_created = ProductVariant.objects.get_or_create(
                    family=family,
                    size=size
                )
                if was_created:
                    created += 1
        self.message_user(request, f'تم إنشاء {created} نسخة جديدة')
    generate_variants.short_description = "إنشاء نسخ لكل المقاسات"
    
    def update_prices(self, request, queryset):
        """تحديث أسعار جميع النسخ"""
        from .services_price_list import CostCalculationService
        for family in queryset:
            CostCalculationService.update_family_prices(family)
        self.message_user(request, f'تم تحديث أسعار {queryset.count()} عائلة')
    update_prices.short_description = "تحديث الأسعار"
    
    def sync_all_variants_to_inventory(self, request, queryset):
        """مزامنة جميع variants مع المخزون"""
        from .models_price_list import ProductVariant
        synced = 0
        created = 0
        
        for family in queryset:
            variants = ProductVariant.objects.filter(family=family)
            for variant in variants:
                try:
                    was_created = variant.sync_to_inventory()
                    if was_created:
                        created += 1
                    else:
                        synced += 1
                except Exception:
                    pass
        
        msg = f'تم مزامنة {synced} منتج'
        if created:
            msg += f' وإنشاء {created} منتج جديد'
        self.message_user(request, msg)
    sync_all_variants_to_inventory.short_description = "🔄 مزامنة كل المقاسات مع المخزون"


# ============ نسخ المنتجات ============

class VariantCostBreakdownInline(admin.TabularInline):
    model = VariantCostBreakdown
    extra = 1
    fields = ['cost_category', 'description', 'material', 'quantity', 'unit_cost', 'amount']
    readonly_fields = ['amount']
    autocomplete_fields = ['material']


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ['sku', 'family', 'size', 'effective_cost_display', 'custom_cost', 'linked_product_display', 'is_active']
    list_filter = ['family', 'is_active']
    search_fields = ['sku', 'barcode', 'family__name']
    autocomplete_fields = ['family', 'size', 'product']
    inlines = [VariantCostBreakdownInline]
    
    fieldsets = (
        ('المعلومات الأساسية', {
            'fields': (('family', 'size'), ('sku', 'barcode'))
        }),
        ('الربط مع المخزون', {
            'fields': ('product',),
            'description': 'المنتج المرتبط في نظام المخزون (يُنشأ تلقائياً عند المزامنة)'
        }),
        ('التكلفة', {
            'fields': (('custom_cost', 'calculated_cost'),),
            'description': 'اترك التكلفة المخصصة فارغة للحساب التلقائي'
        }),
        ('الحالة', {
            'fields': ('is_active',)
        }),
    )
    readonly_fields = ['calculated_cost']
    
    def effective_cost_display(self, obj):
        return f"{obj.effective_cost:,.2f}"
    effective_cost_display.short_description = 'التكلفة الفعلية'
    
    def linked_product_display(self, obj):
        if obj.product:
            return format_html(
                '<a href="{}" style="color: green;">✓ {}</a>',
                reverse('admin:inventory_product_change', args=[obj.product.pk]),
                obj.product.name[:30]
            )
        return format_html('<span style="color: gray;">غير مرتبط</span>')
    linked_product_display.short_description = 'منتج المخزون'
    
    actions = ['sync_to_inventory', 'create_inventory_products']
    
    def sync_to_inventory(self, request, queryset):
        """مزامنة المنتجات المختارة مع المخزون"""
        synced = 0
        created = 0
        errors = []
        
        for variant in queryset:
            try:
                result = variant.sync_to_inventory()
                if result and not variant.product:
                    created += 1
                else:
                    synced += 1
            except Exception as e:
                errors.append(f"{variant}: {str(e)}")
        
        msg = f'تم مزامنة {synced} منتج'
        if created:
            msg += f' وإنشاء {created} منتج جديد'
        self.message_user(request, msg)
        
        if errors:
            self.message_user(request, f'أخطاء: {len(errors)}', level='warning')
    sync_to_inventory.short_description = "🔄 مزامنة مع المخزون"
    
    def create_inventory_products(self, request, queryset):
        """إنشاء منتجات في المخزون للمنتجات غير المرتبطة"""
        queryset = queryset.filter(product__isnull=True)
        created = 0
        
        for variant in queryset:
            try:
                variant.sync_to_inventory()
                created += 1
            except Exception:
                pass
        
        self.message_user(request, f'تم إنشاء {created} منتج جديد في المخزون')
    create_inventory_products.short_description = "➕ إنشاء منتجات في المخزون"


# ============ فئات التكاليف ============

@admin.register(CostCategory)
class CostCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'cost_type', 'is_direct', 'allocation_method', 'default_rate', 'is_active']
    list_filter = ['cost_type', 'is_direct', 'is_active']
    search_fields = ['name']
    ordering = ['sort_order', 'name']
    
    fieldsets = (
        ('المعلومات الأساسية', {
            'fields': ('name', 'description')
        }),
        ('التصنيف', {
            'fields': (('cost_type', 'is_direct'),)
        }),
        ('التوزيع', {
            'fields': (('allocation_method', 'default_rate'),)
        }),
        ('الحالة', {
            'fields': (('sort_order', 'is_active'),)
        }),
    )


# ============ إعدادات التكاليف غير المباشرة ============

@admin.register(OverheadCostSetting)
class OverheadCostSettingAdmin(admin.ModelAdmin):
    list_display = ['name', 'cost_category', 'calculation_method', 'rate', 'families_count', 'is_active']
    list_filter = ['cost_category', 'calculation_method', 'is_active']
    search_fields = ['name']
    filter_horizontal = ['applies_to_families']
    
    fieldsets = (
        ('المعلومات الأساسية', {
            'fields': ('name', 'cost_category')
        }),
        ('الحساب', {
            'fields': (('calculation_method', 'rate'),)
        }),
        ('التطبيق', {
            'fields': ('applies_to_families',),
            'description': 'اتركه فارغاً للتطبيق على جميع العائلات'
        }),
        ('الحالة', {
            'fields': ('is_active',)
        }),
    )
    
    def families_count(self, obj):
        count = obj.applies_to_families.count()
        return count if count > 0 else 'الكل'
    families_count.short_description = 'عدد العائلات'


# ============ قوائم الأسعار ============

class ProductVariantPriceInline(admin.TabularInline):
    model = ProductVariantPrice
    extra = 0
    fields = ['family', 'size', 'custom_price', 'calculated_price', 'final_price', 'is_active']
    readonly_fields = ['calculated_price', 'final_price']
    autocomplete_fields = ['family', 'size']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('family', 'size')


@admin.register(PriceList)
class PriceListAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'list_type', 'discount_percentage', 'tax_info', 'is_default', 'is_active', 'export_links']
    list_editable = ['discount_percentage', 'is_active']
    list_filter = ['list_type', 'includes_tax', 'is_active']
    search_fields = ['code', 'name']
    ordering = ['name']
    # inlines = [ProductVariantPriceInline]  # قد يكون بطيئاً مع عدد كبير من الأسعار
    
    fieldsets = (
        ('المعلومات الأساسية', {
            'fields': (('code', 'name'), 'name_en', 'list_type', 'description')
        }),
        ('التسعير', {
            'fields': (('discount_percentage', 'min_order_amount'),),
            'description': 'نسبة الخصم تُخصم من السعر الأساسي. استخدم قيمة سالبة للزيادة.'
        }),
        ('الضريبة', {
            'fields': (('includes_tax', 'tax_rate'),)
        }),
        ('الصلاحية', {
            'fields': (('valid_from', 'valid_until'),)
        }),
        ('العرض', {
            'fields': ('logo', 'header_text', 'footer_text')
        }),
        ('الحالة', {
            'fields': (('is_default', 'is_active'),)
        }),
    )
    
    def tax_info(self, obj):
        if obj.includes_tax:
            return format_html('<span style="color: green;">شامل {}%</span>', obj.tax_rate)
        return format_html('<span style="color: gray;">غير شامل</span>')
    tax_info.short_description = 'الضريبة'
    
    def export_links(self, obj):
        base_url = reverse('smart_pricing:export_price_list', args=[obj.id])
        return format_html(
            '<a href="{}?format=pdf">PDF</a> | '
            '<a href="{}?format=excel">Excel</a> | '
            '<a href="{}?format=csv">CSV</a>',
            base_url, base_url, base_url
        )
    export_links.short_description = 'تصدير'
    
    actions = ['generate_all_prices', 'export_to_excel', 'export_to_pdf']
    
    def generate_all_prices(self, request, queryset):
        """إنشاء أسعار لجميع المنتجات"""
        from .models_price_list import ProductFamily, ProductVariantPrice
        
        families = ProductFamily.objects.filter(is_active=True, show_in_price_list=True)
        created = 0
        
        for price_list in queryset:
            for family in families:
                for size in family.available_sizes.all():
                    vp, was_created = ProductVariantPrice.objects.get_or_create(
                        family=family,
                        size=size,
                        price_list=price_list
                    )
                    if was_created:
                        created += 1
        
        self.message_user(request, f'تم إنشاء {created} سعر جديد')
    generate_all_prices.short_description = "إنشاء أسعار لجميع المنتجات"
    
    def export_to_excel(self, request, queryset):
        from .export_service import PriceListExporter
        if queryset.count() == 1:
            exporter = PriceListExporter(queryset.first())
            return exporter.export_to_excel()
        self.message_user(request, 'يرجى اختيار قائمة واحدة فقط')
    export_to_excel.short_description = "تصدير Excel"
    
    def export_to_pdf(self, request, queryset):
        from .export_service import PriceListExporter
        if queryset.count() == 1:
            exporter = PriceListExporter(queryset.first())
            return exporter.export_to_pdf()
        self.message_user(request, 'يرجى اختيار قائمة واحدة فقط')
    export_to_pdf.short_description = "تصدير PDF"


# ============ أسعار النسخ ============

@admin.register(ProductVariantPrice)
class ProductVariantPriceAdmin(admin.ModelAdmin):
    list_display = ['family', 'size', 'price_list', 'effective_price_display', 'final_price_display', 'is_custom', 'is_active']
    list_filter = ['price_list', 'family', 'is_active']
    search_fields = ['family__name', 'size__name']
    autocomplete_fields = ['family', 'size', 'price_list']
    
    fieldsets = (
        ('المنتج', {
            'fields': (('family', 'size'),)
        }),
        ('قائمة الأسعار', {
            'fields': ('price_list',)
        }),
        ('السعر', {
            'fields': (('custom_price', 'calculated_price', 'final_price'),),
            'description': 'اترك السعر المخصص فارغاً للحساب التلقائي'
        }),
        ('الحالة', {
            'fields': ('is_active',)
        }),
    )
    readonly_fields = ['calculated_price', 'final_price']
    
    def effective_price_display(self, obj):
        return f"{obj.effective_price:,.2f}"
    effective_price_display.short_description = 'السعر'
    
    def final_price_display(self, obj):
        return f"{obj.final_price:,.2f}"
    final_price_display.short_description = 'السعر النهائي'
    
    def is_custom(self, obj):
        return obj.custom_price is not None
    is_custom.boolean = True
    is_custom.short_description = 'مخصص'


# ============ سجلات التصدير ============

@admin.register(PriceListExport)
class PriceListExportAdmin(admin.ModelAdmin):
    list_display = ['price_list', 'format', 'generated_at', 'generated_by', 'download_link']
    list_filter = ['format', 'price_list', 'generated_at']
    date_hierarchy = 'generated_at'
    readonly_fields = ['price_list', 'format', 'file', 'include_cost', 'include_margin', 
                      'include_tax_breakdown', 'families', 'generated_at', 'generated_by']
    
    def download_link(self, obj):
        if obj.file:
            return format_html('<a href="{}">تحميل</a>', obj.file.url)
        return '-'
    download_link.short_description = 'تحميل'
    
    def has_add_permission(self, request):
        return False  # لا يمكن إضافة سجلات يدوياً


# ============ الإعدادات ============

@admin.register(PriceListSettings)
class PriceListSettingsAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'phone', 'email', 'default_tax_rate']
    
    fieldsets = (
        ('معلومات الشركة', {
            'fields': (('company_name', 'company_name_en'), 'logo', 'address')
        }),
        ('التواصل', {
            'fields': (('phone', 'email'), 'website')
        }),
        ('الضريبة', {
            'fields': (('default_tax_rate', 'tax_registration_number'),)
        }),
        ('نصوص قائمة الأسعار', {
            'fields': ('price_list_header', 'price_list_footer', 'price_validity_text')
        }),
    )
    
    def has_add_permission(self, request):
        # السماح بإضافة سجل واحد فقط
        return not PriceListSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        return False
