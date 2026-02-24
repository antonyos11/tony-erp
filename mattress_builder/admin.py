"""
لوحة التحكم الكاملة لنظام بناء المراتب المخصصة
Full Control Panel for Mattress Builder System
إدارة المقاسات، الطبقات، الأسعار، الإحساس، واقتراحات الذكاء الاصطناعي
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.db.models import Count, Sum, Avg
from .models import (
    MattressFeelingType,
    AIRecommendationConfig,
    MattressSize,
    MattressComponentCategory,
    MattressComponent,
    MattressRecommendationRule,
    CustomMattressDesign,
    DesignComponent,
    MattressTemplate,
    BuilderSettings,
    MattressOrder,
    DesignerCommission,
)


# ==========================================
# 1. إدارة المقاسات والأسعار - كنترول كامل
# ==========================================
@admin.register(MattressSize)
class MattressSizeAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'display_dimensions', 'height_default', 
        'base_price_display', 'price_multiplier', 
        'designs_count', 'is_active', 'sort_order'
    ]
    list_filter = ['is_active']
    list_editable = ['is_active', 'sort_order']
    search_fields = ['name', 'name_en']
    ordering = ['sort_order', 'width']
    
    fieldsets = (
        (_('معلومات أساسية'), {
            'fields': ('name', 'name_en', 'icon'),
            'description': 'أدخل اسم المقاس وأيقونة العرض'
        }),
        (_('الأبعاد (سم)'), {
            'fields': ('width', 'length', 'height_default'),
            'description': 'حدد أبعاد المرتبة بالسنتيمتر'
        }),
        (_('💰 التسعير - تحكم كامل'), {
            'fields': ('base_price', 'price_multiplier'),
            'description': 'السعر الأساسي للمقاس + معامل ضرب السعر. السعر النهائي = السعر الأساسي × معامل السعر'
        }),
        (_('إعدادات العرض'), {
            'fields': ('image', 'is_active', 'sort_order')
        }),
    )
    
    def display_dimensions(self, obj):
        return format_html(
            '<span style="font-weight:600">{} × {} سم</span>',
            obj.width, obj.length
        )
    display_dimensions.short_description = _('الأبعاد')
    
    def base_price_display(self, obj):
        return format_html(
            '<span style="color:#C8A962;font-weight:700;font-size:1.05em">{:,.0f} ج.م</span>',
            obj.base_price
        )
    base_price_display.short_description = _('السعر الأساسي')
    
    def designs_count(self, obj):
        count = obj.designs.count()
        if count > 0:
            return format_html(
                '<span class="badge" style="background:#3b82f6;color:white;padding:3px 8px;border-radius:10px">{}</span>',
                count
            )
        return '0'
    designs_count.short_description = _('عدد التصميمات')


# ==========================================
# 2. إدارة الطبقات (فئات + مكونات) - كنترول كامل
# ==========================================
class MattressComponentInline(admin.TabularInline):
    """عرض المكونات داخل الفئة مباشرة"""
    model = MattressComponent
    extra = 1
    fields = ['name', 'pricing_type', 'base_price', 'price_per_sqm', 
              'quality_level', 'thickness', 'density', 'is_active', 'is_featured']
    show_change_link = True


@admin.register(MattressComponentCategory)
class MattressComponentCategoryAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'category_type', 'layer_order', 'color_preview', 
        'is_required', 'max_selections', 'components_count',
        'is_active', 'sort_order'
    ]
    list_filter = ['category_type', 'is_required', 'is_active']
    list_editable = ['is_active', 'sort_order', 'layer_order', 'is_required', 'max_selections']
    search_fields = ['name', 'name_en', 'description']
    inlines = [MattressComponentInline]
    
    fieldsets = (
        (_('معلومات أساسية'), {
            'fields': ('name', 'name_en', 'category_type', 'description')
        }),
        (_('🎨 إعدادات العرض'), {
            'fields': ('icon', 'color', 'layer_order'),
            'description': 'ترتيب الطبقة من الأسفل (1=قاعدة) للأعلى (5=سطح)'
        }),
        (_('⚙️ قواعد الاختيار'), {
            'fields': ('is_required', 'max_selections'),
            'description': 'حدد هل يجب اختيار مكون من هذه الفئة وعدد الاختيارات المسموحة'
        }),
        (_('الحالة'), {
            'fields': ('is_active', 'sort_order')
        }),
    )
    
    def color_preview(self, obj):
        return format_html(
            '<div style="width:35px;height:25px;background-color:{};border:1px solid #ccc;border-radius:6px;display:inline-block"></div> {}',
            obj.color, obj.color
        )
    color_preview.short_description = _('اللون')
    
    def components_count(self, obj):
        count = obj.components.count()
        active = obj.components.filter(is_active=True).count()
        return format_html(
            '<span title="{} مفعل من {}">{}/{}</span>',
            active, count, active, count
        )
    components_count.short_description = _('المكونات')


@admin.register(MattressComponent)
class MattressComponentAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'category_link', 'quality_badge', 'pricing_display', 
        'thickness_display', 'density', 'popularity_score',
        'is_featured', 'is_popular', 'is_active'
    ]
    list_filter = [
        'category', 'quality_level', 'pricing_type', 
        'is_featured', 'is_popular', 'is_active'
    ]
    list_editable = ['is_featured', 'is_popular', 'is_active']
    search_fields = ['name', 'name_en', 'description']
    filter_horizontal = ['compatible_with', 'incompatible_with']
    autocomplete_fields = ['inventory_product']
    
    fieldsets = (
        (_('معلومات أساسية'), {
            'fields': ('category', 'name', 'name_en', 'description', 'short_description')
        }),
        (_('💰 التسعير - تحكم كامل'), {
            'fields': ('pricing_type', 'base_price', 'price_per_sqm'),
            'description': 'ثابت: سعر ثابت بغض النظر عن المقاس | حسب المساحة: سعر × مساحة المرتبة بالمتر المربع | ثابت + حسب المساحة: سعر أساسي + (سعر × مساحة)'
        }),
        (_('📐 المواصفات الفنية'), {
            'fields': ('quality_level', 'thickness', 'density', 'specifications'),
            'description': 'السماكة بالسنتيمتر، الكثافة بالكيلوجرام/متر مكعب'
        }),
        (_('🎨 الوسائط والعرض'), {
            'fields': ('image', 'icon', 'texture_pattern')
        }),
        (_('📦 الربط بالمخزون'), {
            'fields': ('inventory_product',),
            'classes': ('collapse',),
            'description': 'ربط المكون بمنتج في المخزون لتتبع الكميات'
        }),
        (_('🔗 قواعد التوافق'), {
            'fields': ('compatible_with', 'incompatible_with'),
            'classes': ('collapse',),
            'description': 'حدد المكونات المتوافقة وغير المتوافقة مع هذا المكون'
        }),
        (_('✨ الفوائد والميزات'), {
            'fields': ('benefits',),
            'description': 'أضف قائمة الفوائد كمصفوفة JSON'
        }),
        (_('📊 الحالة والشعبية'), {
            'fields': ('is_active', 'is_featured', 'is_popular', 'popularity_score', 'sort_order')
        }),
    )
    
    actions = ['make_featured', 'remove_featured', 'reset_popularity']
    
    def category_link(self, obj):
        url = reverse('admin:mattress_builder_mattresscomponentcategory_change', args=[obj.category.pk])
        return format_html('<a href="{}">{}</a>', url, obj.category.name)
    category_link.short_description = _('الفئة')
    
    def quality_badge(self, obj):
        colors = {
            'basic': '#94a3b8',
            'standard': '#3b82f6',
            'premium': '#f59e0b',
            'luxury': '#ec4899',
        }
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;border-radius:8px;font-size:0.8em">{}</span>',
            colors.get(obj.quality_level, '#666'),
            obj.get_quality_level_display()
        )
    quality_badge.short_description = _('الجودة')
    
    def pricing_display(self, obj):
        if obj.pricing_type == 'fixed':
            return format_html(
                '<span style="color:#C8A962;font-weight:700">{:,.0f} ج.م</span>',
                obj.base_price
            )
        elif obj.pricing_type == 'per_sqm':
            return format_html(
                '<span style="color:#10b981;font-weight:700">{:,.0f} ج.م/م²</span>',
                obj.price_per_sqm
            )
        else:
            return format_html(
                '<span style="color:#C8A962;font-weight:700">{:,.0f}</span> + '
                '<span style="color:#10b981;font-weight:700">{:,.0f}/م²</span>',
                obj.base_price, obj.price_per_sqm
            )
    pricing_display.short_description = _('💰 التسعير')
    
    def thickness_display(self, obj):
        if obj.thickness:
            return format_html(
                '<span style="background:#f0fdf4;color:#16a34a;padding:2px 8px;border-radius:8px">{} سم</span>',
                obj.thickness
            )
        return '—'
    thickness_display.short_description = _('السماكة')
    
    def make_featured(self, request, queryset):
        queryset.update(is_featured=True)
        self.message_user(request, f'تم تمييز {queryset.count()} مكون')
    make_featured.short_description = _('⭐ تمييز المكونات المختارة')
    
    def remove_featured(self, request, queryset):
        queryset.update(is_featured=False)
        self.message_user(request, f'تم إزالة التمييز عن {queryset.count()} مكون')
    remove_featured.short_description = _('إزالة تمييز المكونات المختارة')
    
    def reset_popularity(self, request, queryset):
        queryset.update(popularity_score=0)
        self.message_user(request, f'تم إعادة ضبط شعبية {queryset.count()} مكون')
    reset_popularity.short_description = _('🔄 إعادة ضبط الشعبية')


# ==========================================
# 3. إدارة إحساس المرتبة - جديد
# ==========================================
@admin.register(MattressFeelingType)
class MattressFeelingTypeAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'firmness_level', 'firmness_score_display', 
        'color_preview', 'extra_price_display', 
        'designs_count', 'is_active', 'sort_order'
    ]
    list_filter = ['firmness_level', 'is_active']
    list_editable = ['is_active', 'sort_order']
    search_fields = ['name', 'name_en', 'description']
    
    fieldsets = (
        (_('📋 معلومات أساسية'), {
            'fields': ('name', 'name_en', 'description', 'icon', 'color')
        }),
        (_('📊 مستوى الصلابة'), {
            'fields': ('firmness_level', 'firmness_score'),
            'description': 'حدد مستوى صلابة المرتبة ودرجته من 1 (ناعم جداً) إلى 10 (صلب جداً)'
        }),
        (_('💰 تسعير إضافي'), {
            'fields': ('extra_price',),
            'description': 'سعر إضافي يُضاف للتصميم عند اختيار هذا الإحساس'
        }),
        (_('🎯 الملاءمة والفوائد'), {
            'fields': ('ideal_for', 'benefits'),
            'description': 'أضف قوائم JSON لمن يناسبه هذا الإحساس والفوائد المرتبطة'
        }),
        (_('🤖 قواعد الكشف التلقائي'), {
            'fields': ('auto_detect_rules',),
            'classes': ('collapse',),
            'description': 'قواعد لتحديد هذا الإحساس تلقائياً بناءً على المكونات المختارة'
        }),
        (_('الحالة'), {
            'fields': ('is_active', 'sort_order')
        }),
    )
    
    def firmness_score_display(self, obj):
        bar_color = '#4ade80' if obj.firmness_score <= 3 else '#fbbf24' if obj.firmness_score <= 6 else '#ef4444'
        width = obj.firmness_score * 10
        return format_html(
            '<div style="display:flex;align-items:center;gap:8px">'
            '<div style="width:100px;height:10px;background:#e5e7eb;border-radius:5px;overflow:hidden">'
            '<div style="width:{}%;height:100%;background:{};border-radius:5px"></div>'
            '</div>'
            '<span style="font-weight:700">{}/10</span>'
            '</div>',
            width, bar_color, obj.firmness_score
        )
    firmness_score_display.short_description = _('درجة الصلابة')
    
    def color_preview(self, obj):
        return format_html(
            '<div style="width:30px;height:20px;background:{};border-radius:4px;border:1px solid #ccc"></div>',
            obj.color
        )
    color_preview.short_description = _('اللون')
    
    def extra_price_display(self, obj):
        if obj.extra_price > 0:
            return format_html(
                '<span style="color:#C8A962;font-weight:700">+{:,.0f} ج.م</span>',
                obj.extra_price
            )
        return '—'
    extra_price_display.short_description = _('سعر إضافي')
    
    def designs_count(self, obj):
        return obj.designs.count()
    designs_count.short_description = _('تصميمات')


# ==========================================
# 4. اقتراحات الذكاء الاصطناعي - جديد
# ==========================================
@admin.register(AIRecommendationConfig)
class AIRecommendationConfigAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'trigger_badge', 'suggestion_badge', 
        'message_style_display', 'priority_display',
        'suggested_component', 'is_active'
    ]
    list_filter = ['trigger_type', 'suggestion_type', 'message_style', 'is_active']
    list_editable = ['is_active']
    search_fields = ['name', 'description', 'message_ar']
    autocomplete_fields = ['suggested_component', 'suggested_feeling']
    
    fieldsets = (
        (_('📋 معلومات أساسية'), {
            'fields': ('name', 'description')
        }),
        (_('🎯 المحفز - متى يظهر الاقتراح'), {
            'fields': ('trigger_type', 'trigger_conditions'),
            'description': 'عند اختيار المقاس | عند إضافة مكون | عند تجاوز الميزانية | دائماً'
        }),
        (_('💡 الاقتراح - ماذا يقترح'), {
            'fields': ('suggestion_type', 'suggestion_data', 'suggested_component', 'suggested_feeling'),
            'description': 'حدد نوع الاقتراح والمكون/الإحساس المقترح'
        }),
        (_('📝 الرسالة'), {
            'fields': ('message_ar', 'message_en', 'icon', 'message_style'),
            'description': 'النص الذي يظهر للعميل'
        }),
        (_('📊 الأولوية والحالة'), {
            'fields': ('priority', 'is_active'),
            'description': 'الأولوية من 0-100، الأعلى يظهر أولاً'
        }),
    )
    
    def trigger_badge(self, obj):
        colors = {
            'on_size_select': '#3b82f6',
            'on_component_add': '#10b981',
            'on_component_remove': '#ef4444',
            'on_budget_exceed': '#f59e0b',
            'on_category_complete': '#8b5cf6',
            'on_feeling_mismatch': '#ec4899',
            'on_thickness_threshold': '#f97316',
            'always': '#6b7280',
        }
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;border-radius:8px;font-size:0.8em">{}</span>',
            colors.get(obj.trigger_type, '#666'),
            obj.get_trigger_type_display()
        )
    trigger_badge.short_description = _('المحفز')
    
    def suggestion_badge(self, obj):
        return format_html(
            '<span style="background:#f1f5f9;color:#475569;padding:2px 8px;border-radius:8px;font-size:0.8em">{}</span>',
            obj.get_suggestion_type_display()
        )
    suggestion_badge.short_description = _('الاقتراح')
    
    def message_style_display(self, obj):
        style_icons = {
            'info': '💡', 'tip': '🎯', 'upgrade': '⬆️',
            'warning': '⚠️', 'success': '✅', 'savings': '💰', 'health': '🏥'
        }
        return f"{style_icons.get(obj.message_style, '📝')} {obj.get_message_style_display()}"
    message_style_display.short_description = _('النمط')
    
    def priority_display(self, obj):
        color = '#10b981' if obj.priority >= 70 else '#f59e0b' if obj.priority >= 40 else '#94a3b8'
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;border-radius:8px;font-weight:700">{}</span>',
            color, obj.priority
        )
    priority_display.short_description = _('الأولوية')


# ==========================================
# 5. قواعد الاقتراحات (القديمة)
# ==========================================
@admin.register(MattressRecommendationRule)
class MattressRecommendationRuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'condition_type', 'action_type', 'message_type', 'priority', 'is_active']
    list_filter = ['condition_type', 'action_type', 'message_type', 'is_active']
    list_editable = ['is_active', 'priority']
    search_fields = ['name', 'description', 'message']
    fieldsets = (
        (_('معلومات أساسية'), {
            'fields': ('name', 'description')
        }),
        (_('الشرط'), {
            'fields': ('condition_type', 'condition_data')
        }),
        (_('الإجراء'), {
            'fields': ('action_type', 'action_data')
        }),
        (_('الرسالة'), {
            'fields': ('message', 'message_type')
        }),
        (_('الأولوية والحالة'), {
            'fields': ('priority', 'is_active')
        }),
    )


# ==========================================
# 6. إدارة التصميمات
# ==========================================
class DesignComponentInline(admin.TabularInline):
    model = DesignComponent
    extra = 0
    fields = ['component', 'quantity', 'layer_position', 'price_at_selection', 'custom_specifications']
    readonly_fields = ['price_at_selection']
    autocomplete_fields = ['component']


@admin.register(CustomMattressDesign)
class CustomMattressDesignAdmin(admin.ModelAdmin):
    list_display = [
        'design_name', 'customer_name', 'mattress_size', 
        'feeling_display', 'final_price_display',
        'status_badge', 'created_at', 'actions_column'
    ]
    list_filter = ['status', 'feeling_type', 'created_at', 'submitted_at', 'approved_at']
    search_fields = [
        'design_name', 'customer_name', 'customer_phone', 'customer_email', 
        'customer__username', 'customer__first_name'
    ]
    readonly_fields = [
        'base_price', 'components_price', 'final_price', 'created_at', 
        'updated_at', 'submitted_at', 'approved_at', 'view_count',
        'feeling_auto_detected', 'feeling_score'
    ]
    inlines = [DesignComponentInline]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        (_('معلومات العميل'), {
            'fields': ('customer', 'customer_name', 'customer_phone', 'customer_email')
        }),
        (_('التصميم'), {
            'fields': ('design_name', 'mattress_size', 'preview_image')
        }),
        (_('🎭 إحساس المرتبة'), {
            'fields': ('feeling_type', 'feeling_score', 'feeling_auto_detected'),
            'description': 'يمكن تحديد الإحساس يدوياً أو تركه للكشف التلقائي'
        }),
        (_('التفاصيل'), {
            'fields': ('design_data', 'notes', 'admin_notes'),
            'classes': ('collapse',)
        }),
        (_('💰 التسعير'), {
            'fields': ('base_price', 'components_price', 'discount_amount', 'final_price')
        }),
        (_('الحالة'), {
            'fields': ('status', 'approved_by', 'approved_at', 'rejection_reason')
        }),
        (_('الإنتاج'), {
            'fields': ('production_order', 'estimated_production_days'),
            'classes': ('collapse',)
        }),
        (_('معلومات إضافية'), {
            'fields': ('view_count', 'is_template', 'created_at', 'updated_at', 'submitted_at')
        }),
    )
    
    actions = ['approve_designs', 'reject_designs', 'mark_in_production', 'auto_detect_feelings']
    
    def feeling_display(self, obj):
        if obj.feeling_type:
            auto = ' 🤖' if obj.feeling_auto_detected else ''
            return format_html(
                '<span style="background:{};color:white;padding:2px 10px;border-radius:8px">{}{} ({})</span>',
                obj.feeling_type.color, obj.feeling_type.name, auto, obj.feeling_score
            )
        return format_html('<span style="color:#94a3b8">لم يحدد</span>')
    feeling_display.short_description = _('الإحساس')
    
    def final_price_display(self, obj):
        return format_html(
            '<span style="color:#C8A962;font-weight:700;font-size:1.05em">{:,.0f} ج.م</span>',
            obj.final_price
        )
    final_price_display.short_description = _('السعر النهائي')
    
    def status_badge(self, obj):
        colors = {
            'draft': '#6b7280',
            'pending_approval': '#f59e0b',
            'approved': '#10b981',
            'rejected': '#ef4444',
            'in_production': '#3b82f6',
            'completed': '#059669',
            'cancelled': '#6b7280',
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background-color:{};color:white;padding:3px 10px;border-radius:8px;font-size:0.85em">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = _('الحالة')
    
    def actions_column(self, obj):
        if obj.status == 'pending_approval':
            approve_url = reverse('admin:mattress_builder_custommattressdesign_change', args=[obj.pk])
            return format_html(
                '<a class="button" href="{}" style="background:#10b981;color:white;padding:4px 12px;border-radius:6px;text-decoration:none">مراجعة</a>',
                approve_url
            )
        return '—'
    actions_column.short_description = _('إجراءات')
    
    def approve_designs(self, request, queryset):
        count = 0
        for design in queryset.filter(status='pending_approval'):
            design.approve(request.user)
            count += 1
        self.message_user(request, f'تمت الموافقة على {count} تصميم')
    approve_designs.short_description = _('✅ الموافقة على التصميمات المختارة')
    
    def reject_designs(self, request, queryset):
        count = 0
        for design in queryset.filter(status='pending_approval'):
            design.reject('رفض جماعي من الإدارة', request.user)
            count += 1
        self.message_user(request, f'تم رفض {count} تصميم')
    reject_designs.short_description = _('❌ رفض التصميمات المختارة')
    
    def mark_in_production(self, request, queryset):
        count = queryset.filter(status='approved').update(status='in_production')
        self.message_user(request, f'تم تحويل {count} تصميم للإنتاج')
    mark_in_production.short_description = _('🏭 تحويل للإنتاج')
    
    def auto_detect_feelings(self, request, queryset):
        count = 0
        for design in queryset:
            result = design.auto_detect_feeling()
            if result:
                count += 1
        self.message_user(request, f'تم كشف إحساس {count} تصميم تلقائياً')
    auto_detect_feelings.short_description = _('🤖 كشف الإحساس تلقائياً')
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.customer_name = obj.customer.get_full_name() or obj.customer.username
            obj.customer_email = obj.customer.email
        super().save_model(request, obj, form, change)


# ==========================================
# 7. القوالب
# ==========================================
@admin.register(MattressTemplate)
class MattressTemplateAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'target_audience', 'starting_price', 'discount_percent', 
        'usage_count', 'is_featured', 'is_popular', 'is_active'
    ]
    list_filter = ['target_audience', 'is_featured', 'is_popular', 'is_active']
    list_editable = ['is_featured', 'is_active']
    search_fields = ['name', 'name_en', 'description']
    fieldsets = (
        (_('معلومات أساسية'), {
            'fields': ('name', 'name_en', 'description', 'short_description')
        }),
        (_('التصميم'), {
            'fields': ('base_design', 'template_data', 'target_audience')
        }),
        (_('💰 التسعير'), {
            'fields': ('starting_price', 'discount_percent')
        }),
        (_('الوسائط'), {
            'fields': ('image', 'icon')
        }),
        (_('الميزات'), {
            'fields': ('features',)
        }),
        (_('الحالة'), {
            'fields': ('is_active', 'is_featured', 'is_popular', 'usage_count', 'sort_order')
        }),
    )


# ==========================================
# 8. إعدادات النظام
# ==========================================
@admin.register(BuilderSettings)
class BuilderSettingsAdmin(admin.ModelAdmin):
    list_display = [
        '__str__', 'profit_margin_percent', 'enable_auto_approval',
        'enable_recommendations', 'enable_ai_suggestions',
        'enable_feeling_detection', 'enable_gamification'
    ]
    
    fieldsets = (
        (_('💰 التسعير'), {
            'fields': ('profit_margin_percent',)
        }),
        (_('✅ الموافقات'), {
            'fields': ('enable_auto_approval', 'auto_approval_threshold')
        }),
        (_('🏭 الإنتاج'), {
            'fields': ('estimated_production_days',)
        }),
        (_('📊 القيود'), {
            'fields': ('max_designs_per_customer',)
        }),
        (_('🤖 الذكاء الاصطناعي والاقتراحات'), {
            'fields': (
                'enable_recommendations', 'enable_ai_suggestions',
                'max_ai_suggestions'
            ),
            'description': 'تحكم في اقتراحات الذكاء الاصطناعي وعددها'
        }),
        (_('🎭 إحساس المرتبة'), {
            'fields': ('enable_feeling_detection', 'enable_feeling_selection'),
            'description': 'تفعيل/تعطيل كشف الإحساس التلقائي واختياره يدوياً'
        }),
        (_('🎮 الميزات'), {
            'fields': ('enable_gamification',)
        }),
        (_('🌍 تصميمات المجتمع والعمولات'), {
            'fields': (
                'enable_community_designs', 'enable_duplicate_detection',
                'designer_commission_rate'
            ),
            'description': 'تفعيل تصميمات المجتمع وكشف التصاميم المكررة ونسبة عمولة المصممين'
        }),
        (_('💬 الرسائل'), {
            'fields': ('welcome_message',)
        }),
    )
    
    def has_add_permission(self, request):
        return not BuilderSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        return False


# ==========================================
# 9. إدارة طلبات المراتب المخصصة
# ==========================================
@admin.register(MattressOrder)
class MattressOrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_number', 'customer', 'design', 'status',
        'total', 'payment_method', 'is_community_purchase',
        'created_at'
    ]
    list_filter = ['status', 'payment_method', 'is_community_purchase', 'created_at']
    search_fields = ['order_number', 'customer__username', 'customer__first_name',
                     'customer_name', 'customer_phone']
    readonly_fields = [
        'order_number', 'customer', 'design', 'subtotal', 'tax',
        'total', 'paid_at', 'production_order', 'journal_entry',
        'created_at', 'updated_at'
    ]
    list_per_page = 25
    date_hierarchy = 'created_at'
    
    fieldsets = (
        (_('معلومات الطلب'), {
            'fields': ('order_number', 'customer', 'design', 'status')
        }),
        (_('المبالغ'), {
            'fields': ('subtotal', 'shipping_cost', 'discount', 'tax', 'total')
        }),
        (_('الدفع'), {
            'fields': ('payment_method', 'payment_reference', 'paid_at')
        }),
        (_('بيانات العميل'), {
            'fields': ('customer_name', 'customer_phone', 'customer_email',
                       'shipping_address', 'shipping_city', 'customer_notes')
        }),
        (_('تصميم مجتمعي'), {
            'fields': ('is_community_purchase', 'original_designer'),
            'classes': ('collapse',)
        }),
        (_('التسليم'), {
            'fields': ('estimated_delivery_date', 'actual_delivery_date')
        }),
        (_('الربط'), {
            'fields': ('production_order', 'journal_entry'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_paid', 'mark_in_production', 'mark_delivered']
    
    def mark_paid(self, request, queryset):
        for order in queryset.filter(status='pending_payment'):
            order.mark_as_paid('cash')
        self.message_user(request, f'تم تأكيد الدفع لـ {queryset.count()} طلب')
    mark_paid.short_description = 'تأكيد الدفع'
    
    def mark_in_production(self, request, queryset):
        queryset.filter(status='paid').update(status='in_production')
        self.message_user(request, 'تم تحويل للإنتاج')
    mark_in_production.short_description = 'تحويل للإنتاج'
    
    def mark_delivered(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='delivered', actual_delivery_date=timezone.now().date())
        self.message_user(request, 'تم التسليم')
    mark_delivered.short_description = 'تأكيد التسليم'


# ==========================================
# 10. إدارة عمولات المصممين
# ==========================================
@admin.register(DesignerCommission)
class DesignerCommissionAdmin(admin.ModelAdmin):
    list_display = [
        'designer', 'design', 'order', 'commission_amount',
        'commission_rate', 'status', 'created_at'
    ]
    list_filter = ['status', 'created_at']
    search_fields = ['designer__username', 'designer__first_name', 'order__order_number']
    readonly_fields = ['designer', 'order', 'design', 'commission_rate',
                       'commission_amount', 'created_at']
    list_per_page = 25
    date_hierarchy = 'created_at'
    
    fieldsets = (
        (_('معلومات العمولة'), {
            'fields': ('designer', 'order', 'design')
        }),
        (_('المبلغ'), {
            'fields': ('commission_rate', 'commission_amount')
        }),
        (_('الحالة'), {
            'fields': ('status',)
        }),
        (_('القيد المحاسبي'), {
            'fields': ('journal_entry',),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_commissions', 'mark_paid']
    
    def approve_commissions(self, request, queryset):
        queryset.filter(status='pending').update(status='approved')
        self.message_user(request, f'تم اعتماد {queryset.count()} عمولة')
    approve_commissions.short_description = 'اعتماد العمولات'
    
    def mark_paid(self, request, queryset):
        queryset.filter(status='approved').update(status='paid')
        self.message_user(request, f'تم صرف {queryset.count()} عمولة')
    mark_paid.short_description = 'تأكيد الصرف'

