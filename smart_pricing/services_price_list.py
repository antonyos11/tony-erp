"""
خدمات حساب التكلفة المتقدمة
Advanced Cost Calculation Services

يشمل:
- حساب التكاليف المباشرة (مواد + عمالة)
- حساب التكاليف غير المباشرة
- توزيع المصاريف
- حساب سعر البيع بناءً على هامش الربح
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple
from django.db.models import Sum, F
from django.utils import timezone


class CostCalculationService:
    """خدمة حساب التكلفة للمنتجات"""
    
    @staticmethod
    def calculate_variant_cost(variant, recalculate_breakdown: bool = False) -> Dict:
        """
        حساب التكلفة الكاملة لنسخة منتج
        
        Args:
            variant: ProductVariant instance
            recalculate_breakdown: إعادة حساب التفاصيل من الـ BOM
            
        Returns:
            {
                'direct_material_cost': Decimal,
                'direct_labor_cost': Decimal,
                'manufacturing_overhead': Decimal,
                'total_direct_cost': Decimal,
                'total_indirect_cost': Decimal,
                'total_cost': Decimal,
                'cost_per_unit': Decimal,
                'breakdown': [...]
            }
        """
        from .models_price_list import VariantCostBreakdown, CostCategory, OverheadCostSetting
        
        # تكاليف مباشرة
        direct_material_cost = Decimal('0')
        direct_labor_cost = Decimal('0')
        
        # تكاليف غير مباشرة
        manufacturing_overhead = Decimal('0')
        selling_expense = Decimal('0')
        admin_expense = Decimal('0')
        other_costs = Decimal('0')
        
        breakdown = []
        
        # جمع التكاليف من التفاصيل المحفوظة
        cost_items = VariantCostBreakdown.objects.filter(variant=variant).select_related('cost_category')
        
        for item in cost_items:
            amount = item.amount or Decimal('0')
            breakdown.append({
                'category': item.cost_category.name,
                'type': item.cost_category.cost_type,
                'is_direct': item.cost_category.is_direct,
                'description': item.description,
                'amount': amount,
            })
            
            if item.cost_category.cost_type == 'direct_material':
                direct_material_cost += amount
            elif item.cost_category.cost_type == 'direct_labor':
                direct_labor_cost += amount
            elif item.cost_category.cost_type == 'manufacturing_overhead':
                manufacturing_overhead += amount
            elif item.cost_category.cost_type == 'selling_expense':
                selling_expense += amount
            elif item.cost_category.cost_type == 'admin_expense':
                admin_expense += amount
            else:
                other_costs += amount
        
        # إضافة التكاليف غير المباشرة من الإعدادات
        overhead_settings = OverheadCostSetting.objects.filter(is_active=True)
        
        for setting in overhead_settings:
            # تحقق من التطبيق على هذه العائلة
            if setting.applies_to_families.exists():
                if not setting.applies_to_families.filter(pk=variant.family.pk).exists():
                    continue
            
            overhead_amount = Decimal('0')
            
            if setting.calculation_method == 'fixed_per_unit':
                overhead_amount = setting.rate
                
            elif setting.calculation_method == 'percentage_of_direct':
                total_direct = direct_material_cost + direct_labor_cost
                overhead_amount = total_direct * setting.rate / 100
                
            elif setting.calculation_method == 'percentage_of_material':
                overhead_amount = direct_material_cost * setting.rate / 100
                
            elif setting.calculation_method == 'per_square_meter':
                area = variant.size.area if hasattr(variant.size, 'area') else Decimal('1')
                overhead_amount = setting.rate * Decimal(str(area))
                
            elif setting.calculation_method == 'per_labor_hour':
                # يمكن تحسينها لاحقاً بربطها بساعات العمل الفعلية
                overhead_amount = setting.rate
            
            if overhead_amount > 0:
                manufacturing_overhead += overhead_amount
                breakdown.append({
                    'category': setting.name,
                    'type': setting.cost_category.cost_type,
                    'is_direct': False,
                    'description': f'تكلفة غير مباشرة - {setting.get_calculation_method_display()}',
                    'amount': overhead_amount,
                })
        
        # الإجماليات
        total_direct_cost = direct_material_cost + direct_labor_cost
        total_indirect_cost = manufacturing_overhead + selling_expense + admin_expense + other_costs
        total_cost = total_direct_cost + total_indirect_cost
        
        return {
            'direct_material_cost': direct_material_cost.quantize(Decimal('0.01'), ROUND_HALF_UP),
            'direct_labor_cost': direct_labor_cost.quantize(Decimal('0.01'), ROUND_HALF_UP),
            'manufacturing_overhead': manufacturing_overhead.quantize(Decimal('0.01'), ROUND_HALF_UP),
            'selling_expense': selling_expense.quantize(Decimal('0.01'), ROUND_HALF_UP),
            'admin_expense': admin_expense.quantize(Decimal('0.01'), ROUND_HALF_UP),
            'other_costs': other_costs.quantize(Decimal('0.01'), ROUND_HALF_UP),
            'total_direct_cost': total_direct_cost.quantize(Decimal('0.01'), ROUND_HALF_UP),
            'total_indirect_cost': total_indirect_cost.quantize(Decimal('0.01'), ROUND_HALF_UP),
            'total_cost': total_cost.quantize(Decimal('0.01'), ROUND_HALF_UP),
            'breakdown': breakdown,
        }
    
    @staticmethod
    def calculate_cost_from_bom(variant) -> Dict:
        """
        حساب التكلفة من قائمة المواد (BOM)
        
        Args:
            variant: ProductVariant instance
            
        Returns:
            تفاصيل التكلفة
        """
        from production.models import BillOfMaterials, BOMItem
        from .models_price_list import VariantCostBreakdown, CostCategory
        
        # البحث عن BOM للمنتج المرتبط
        product = variant.product
        if not product:
            return {'error': 'لا يوجد منتج مرتبط', 'total_cost': Decimal('0')}
        
        bom = BillOfMaterials.objects.filter(
            product=product,
            is_active=True,
            is_default=True
        ).first()
        
        if not bom:
            return {'error': 'لا توجد قائمة مواد', 'total_cost': Decimal('0')}
        
        # حساب تكلفة المواد
        material_cost = Decimal('0')
        material_details = []
        
        bom_items = BOMItem.objects.filter(bom=bom).select_related('material')
        for item in bom_items:
            qty_with_wastage = item.quantity * (1 + item.wastage_percentage / 100)
            item_cost = qty_with_wastage * (item.material.cost or Decimal('0'))
            material_cost += item_cost
            
            material_details.append({
                'material': item.material.name,
                'quantity': item.quantity,
                'wastage': item.wastage_percentage,
                'unit_cost': item.material.cost,
                'total_cost': item_cost,
            })
        
        return {
            'material_cost': material_cost.quantize(Decimal('0.01'), ROUND_HALF_UP),
            'labor_cost': bom.total_labor_cost,
            'overhead_cost': bom.total_overhead_cost,
            'total_cost': (material_cost + bom.total_labor_cost + bom.total_overhead_cost).quantize(Decimal('0.01'), ROUND_HALF_UP),
            'material_details': material_details,
        }
    
    @staticmethod
    def calculate_selling_price(cost: Decimal, margin_percentage: Decimal) -> Decimal:
        """
        حساب سعر البيع بناءً على التكلفة وهامش الربح
        
        Args:
            cost: التكلفة الإجمالية
            margin_percentage: نسبة هامش الربح المطلوبة
            
        Returns:
            سعر البيع
        """
        if cost <= 0:
            return Decimal('0')
        
        selling_price = cost * (1 + margin_percentage / 100)
        return selling_price.quantize(Decimal('0.01'), ROUND_HALF_UP)
    
    @staticmethod
    def calculate_margin(selling_price: Decimal, cost: Decimal) -> Dict:
        """
        حساب هامش الربح
        
        Returns:
            {
                'margin_amount': المبلغ,
                'margin_percentage': النسبة,
                'markup_percentage': نسبة الربح على التكلفة
            }
        """
        if cost <= 0:
            return {
                'margin_amount': selling_price,
                'margin_percentage': Decimal('100'),
                'markup_percentage': Decimal('0'),
            }
        
        margin_amount = selling_price - cost
        margin_percentage = (margin_amount / selling_price * 100) if selling_price > 0 else Decimal('0')
        markup_percentage = (margin_amount / cost * 100)
        
        return {
            'margin_amount': margin_amount.quantize(Decimal('0.01'), ROUND_HALF_UP),
            'margin_percentage': margin_percentage.quantize(Decimal('0.01'), ROUND_HALF_UP),
            'markup_percentage': markup_percentage.quantize(Decimal('0.01'), ROUND_HALF_UP),
        }
    
    @staticmethod
    def update_family_prices(family, base_cost: Optional[Decimal] = None):
        """
        تحديث أسعار جميع نسخ العائلة
        
        Args:
            family: ProductFamily instance
            base_cost: التكلفة الأساسية الجديدة (اختياري)
        """
        from .models_price_list import ProductVariant, ProductVariantPrice, PriceList
        
        if base_cost is not None:
            family.base_cost = base_cost
            family.save()
        
        # تحديث تكاليف النسخ
        variants = ProductVariant.objects.filter(family=family)
        for variant in variants:
            if not variant.custom_cost:
                variant.calculated_cost = family.base_cost * variant.size.cost_multiplier
                variant.save()
        
        # تحديث الأسعار في جميع القوائم
        variant_prices = ProductVariantPrice.objects.filter(family=family)
        for vp in variant_prices:
            vp.calculate_prices()
            vp.save()
    
    @staticmethod
    def bulk_update_costs(family, size_costs: Dict[int, Decimal]):
        """
        تحديث تكاليف متعددة دفعة واحدة
        
        Args:
            family: ProductFamily instance
            size_costs: {size_id: cost} - قاموس بالتكاليف لكل مقاس
        """
        from .models_price_list import ProductVariant
        
        for size_id, cost in size_costs.items():
            ProductVariant.objects.filter(
                family=family,
                size_id=size_id
            ).update(custom_cost=cost)


class PriceListService:
    """خدمة إدارة قوائم الأسعار"""
    
    @staticmethod
    def generate_price_matrix(price_list, families=None) -> List[Dict]:
        """
        توليد مصفوفة الأسعار لقائمة أسعار معينة
        
        Args:
            price_list: PriceList instance
            families: قائمة العائلات (اختياري، فارغ = كل العائلات)
            
        Returns:
            قائمة من القواميس تمثل الجدول
        """
        from .models_price_list import ProductFamily, ProductSize, ProductVariantPrice
        
        if families is None:
            families = ProductFamily.objects.filter(
                is_active=True,
                show_in_price_list=True
            ).order_by('sort_order', 'name')
        
        # جمع كل المقاسات المستخدمة
        all_sizes = ProductSize.objects.filter(
            is_active=True,
            product_families__in=families
        ).distinct().order_by('sort_order', 'width', 'length')
        
        matrix = []
        
        for family in families:
            row = {
                'family_id': family.id,
                'family_code': family.code,
                'family_name': family.name,
                'family_name_en': family.name_en,
                'base_price': family.base_price,
                'base_cost': family.base_cost,
                'prices': {}
            }
            
            # جمع أسعار كل مقاس
            variant_prices = ProductVariantPrice.objects.filter(
                family=family,
                price_list=price_list,
                is_active=True
            ).select_related('size')
            
            for vp in variant_prices:
                size_key = f"{vp.size.width}x{vp.size.length}"
                row['prices'][size_key] = {
                    'size_id': vp.size.id,
                    'size_name': str(vp.size),
                    'price': vp.effective_price,
                    'price_with_tax': vp.final_price,
                    'is_custom': vp.custom_price is not None,
                }
            
            # حساب الأسعار للمقاسات غير المحفوظة
            for size in family.available_sizes.all():
                size_key = f"{size.width}x{size.length}"
                if size_key not in row['prices']:
                    base_price = family.base_price * size.price_multiplier
                    discounted_price = price_list.apply_discount(base_price)
                    final_price = price_list.apply_tax(discounted_price)
                    
                    row['prices'][size_key] = {
                        'size_id': size.id,
                        'size_name': str(size),
                        'price': discounted_price,
                        'price_with_tax': final_price,
                        'is_custom': False,
                    }
            
            matrix.append(row)
        
        return matrix
    
    @staticmethod
    def apply_bulk_discount(price_list, discount_percentage: Decimal, families=None):
        """
        تطبيق خصم جماعي على قائمة أسعار
        
        Args:
            price_list: PriceList instance
            discount_percentage: نسبة الخصم
            families: العائلات المستهدفة (فارغ = الكل)
        """
        from .models_price_list import ProductVariantPrice
        
        query = ProductVariantPrice.objects.filter(price_list=price_list)
        if families:
            query = query.filter(family__in=families)
        
        for vp in query:
            if vp.custom_price:
                vp.custom_price = vp.custom_price * (1 - discount_percentage / 100)
            vp.save()
    
    @staticmethod
    def copy_price_list(source_price_list, new_name: str, new_code: str, 
                        discount_adjustment: Decimal = Decimal('0')) -> 'PriceList':
        """
        نسخ قائمة أسعار مع إمكانية تعديل الخصم
        
        Args:
            source_price_list: القائمة المصدر
            new_name: اسم القائمة الجديدة
            new_code: كود القائمة الجديدة
            discount_adjustment: تعديل الخصم (سالب = زيادة)
            
        Returns:
            القائمة الجديدة
        """
        from .models_price_list import PriceList, ProductVariantPrice
        
        # نسخ القائمة
        new_list = PriceList.objects.create(
            code=new_code,
            name=new_name,
            list_type=source_price_list.list_type,
            description=f'منسوخة من: {source_price_list.name}',
            discount_percentage=source_price_list.discount_percentage + discount_adjustment,
            includes_tax=source_price_list.includes_tax,
            tax_rate=source_price_list.tax_rate,
            currency=source_price_list.currency,
        )
        
        # نسخ الأسعار المخصصة
        source_prices = ProductVariantPrice.objects.filter(
            price_list=source_price_list,
            custom_price__isnull=False
        )
        
        for sp in source_prices:
            adjusted_price = sp.custom_price * (1 - discount_adjustment / 100) if sp.custom_price else None
            ProductVariantPrice.objects.create(
                family=sp.family,
                size=sp.size,
                price_list=new_list,
                custom_price=adjusted_price,
            )
        
        return new_list
    
    @staticmethod
    def get_price_comparison(product_family, sizes=None) -> List[Dict]:
        """
        مقارنة الأسعار بين قوائم الأسعار المختلفة
        
        Args:
            product_family: ProductFamily instance
            sizes: قائمة المقاسات (فارغ = كل المقاسات)
            
        Returns:
            قائمة المقارنات
        """
        from .models_price_list import PriceList, ProductVariantPrice
        
        if sizes is None:
            sizes = product_family.available_sizes.all()
        
        price_lists = PriceList.objects.filter(is_active=True).order_by('name')
        
        comparison = []
        for size in sizes:
            row = {
                'size': str(size),
                'size_id': size.id,
                'prices': {}
            }
            
            for pl in price_lists:
                vp = ProductVariantPrice.objects.filter(
                    family=product_family,
                    size=size,
                    price_list=pl
                ).first()
                
                if vp:
                    row['prices'][pl.code] = {
                        'list_name': pl.name,
                        'price': vp.effective_price,
                        'price_with_tax': vp.final_price,
                        'includes_tax': pl.includes_tax,
                    }
                else:
                    # حساب السعر
                    base_price = product_family.base_price * size.price_multiplier
                    discounted = pl.apply_discount(base_price)
                    final = pl.apply_tax(discounted)
                    row['prices'][pl.code] = {
                        'list_name': pl.name,
                        'price': discounted,
                        'price_with_tax': final,
                        'includes_tax': pl.includes_tax,
                    }
            
            comparison.append(row)
        
        return comparison


class InvoicePricingService:
    """
    خدمة تسعير الفواتير
    Invoice Pricing Service
    
    تستخدم لاختيار السعر الصحيح من قائمة الأسعار المناسبة عند إنشاء الفواتير
    """
    
    @staticmethod
    def get_customer_price_list(customer):
        """
        الحصول على قائمة الأسعار المناسبة للعميل
        
        Args:
            customer: Customer instance (من sales أو core)
            
        Returns:
            PriceList instance أو None
        """
        from .models_price_list import PriceList
        
        # إذا كان للعميل قائمة أسعار مخصصة
        if hasattr(customer, 'price_list') and customer.price_list:
            return customer.price_list
        
        # تحديد نوع القائمة بناءً على نوع العميل
        customer_type = getattr(customer, 'customer_type', None) or getattr(customer, 'type', 'retail')
        
        type_mapping = {
            'retail': 'retail',          # تجزئة
            'wholesale': 'wholesale',     # جملة
            'distributor': 'distributor', # موزعين
            'vip': 'vip',                 # VIP
            'agent': 'distributor',       # وكيل = موزع
        }
        
        list_type = type_mapping.get(customer_type, 'retail')
        
        # البحث عن قائمة أسعار نشطة من النوع المطلوب
        price_list = PriceList.objects.filter(
            list_type=list_type,
            is_active=True
        ).first()
        
        # إذا لم توجد، استخدم قائمة التجزئة
        if not price_list:
            price_list = PriceList.objects.filter(
                list_type='retail',
                is_active=True
            ).first()
        
        return price_list
    
    @staticmethod
    def get_product_price(product, customer=None, price_list=None, quantity=1):
        """
        الحصول على سعر المنتج للعميل
        
        Args:
            product: Product instance من inventory
            customer: Customer instance (اختياري)
            price_list: PriceList instance (اختياري - يتجاوز قائمة العميل)
            quantity: الكمية (للخصومات الكمية)
            
        Returns:
            {
                'unit_price': السعر الأساسي,
                'unit_price_with_tax': السعر شامل الضريبة,
                'price_list': قائمة الأسعار المستخدمة,
                'discount_percentage': نسبة الخصم,
                'includes_tax': هل شامل الضريبة,
                'tax_rate': نسبة الضريبة
            }
        """
        from .models_price_list import PriceList, ProductVariantPrice, ProductVariant
        
        # تحديد قائمة الأسعار
        if price_list is None and customer is not None:
            price_list = InvoicePricingService.get_customer_price_list(customer)
        
        if price_list is None:
            price_list = PriceList.objects.filter(
                list_type='retail',
                is_active=True
            ).first()
        
        # البحث عن الـ variant المرتبط بالمنتج
        variant = ProductVariant.objects.filter(
            product=product
        ).select_related('family').first()
        
        result = {
            'unit_price': product.price if product else Decimal('0'),
            'unit_price_with_tax': product.price if product else Decimal('0'),
            'price_list': price_list,
            'discount_percentage': Decimal('0'),
            'includes_tax': False,
            'tax_rate': Decimal('0'),
            'quantity_discount': Decimal('0'),
        }
        
        if not price_list:
            return result
        
        if variant:
            # البحث عن سعر مخصص
            variant_price = ProductVariantPrice.objects.filter(
                family=variant.family,
                size=variant.size,
                price_list=price_list
            ).first()
            
            if variant_price:
                result['unit_price'] = variant_price.effective_price
                result['unit_price_with_tax'] = variant_price.final_price
            else:
                # حساب السعر من السعر الأساسي
                base_price = variant.family.base_price * variant.size.price_multiplier
                result['unit_price'] = price_list.apply_discount(base_price)
                result['unit_price_with_tax'] = price_list.apply_tax(result['unit_price'])
        else:
            # استخدام سعر المنتج مباشرة مع خصم القائمة
            result['unit_price'] = price_list.apply_discount(product.price)
            result['unit_price_with_tax'] = price_list.apply_tax(result['unit_price'])
        
        result['discount_percentage'] = price_list.discount_percentage
        result['includes_tax'] = price_list.includes_tax
        result['tax_rate'] = price_list.tax_rate
        
        # خصم كمية (إذا كان متاحاً)
        result['quantity_discount'] = InvoicePricingService.get_quantity_discount(
            product, quantity, price_list
        )
        
        if result['quantity_discount'] > 0:
            discount_factor = 1 - (result['quantity_discount'] / 100)
            result['unit_price'] *= discount_factor
            result['unit_price_with_tax'] *= discount_factor
        
        return result
    
    @staticmethod
    def get_quantity_discount(product, quantity, price_list=None):
        """
        حساب خصم الكمية
        
        يمكن تخصيص هذه الدالة حسب سياسة الخصومات
        """
        # مثال بسيط لخصومات الكمية
        if quantity >= 100:
            return Decimal('10')  # 10% خصم لـ 100+ وحدة
        elif quantity >= 50:
            return Decimal('7')   # 7% خصم لـ 50+ وحدة
        elif quantity >= 20:
            return Decimal('5')   # 5% خصم لـ 20+ وحدة
        elif quantity >= 10:
            return Decimal('3')   # 3% خصم لـ 10+ وحدة
        return Decimal('0')
    
    @staticmethod
    def calculate_line_total(product, quantity, customer=None, price_list=None):
        """
        حساب إجمالي سطر الفاتورة
        
        Returns:
            {
                'quantity': الكمية,
                'unit_price': سعر الوحدة,
                'unit_price_with_tax': سعر الوحدة شامل الضريبة,
                'line_total': إجمالي السطر,
                'line_total_with_tax': إجمالي السطر شامل الضريبة,
                'discount_amount': مبلغ الخصم,
                'tax_amount': مبلغ الضريبة,
            }
        """
        pricing = InvoicePricingService.get_product_price(
            product, customer, price_list, quantity
        )
        
        line_total = pricing['unit_price'] * quantity
        line_total_with_tax = pricing['unit_price_with_tax'] * quantity
        
        # حساب مبلغ الخصم
        original_price = product.price * quantity if product else Decimal('0')
        discount_amount = original_price - line_total
        
        # حساب مبلغ الضريبة
        tax_amount = line_total_with_tax - line_total
        
        return {
            'quantity': quantity,
            'unit_price': pricing['unit_price'],
            'unit_price_with_tax': pricing['unit_price_with_tax'],
            'line_total': line_total,
            'line_total_with_tax': line_total_with_tax,
            'discount_amount': discount_amount if discount_amount > 0 else Decimal('0'),
            'tax_amount': tax_amount,
            'price_list': pricing['price_list'],
            'discount_percentage': pricing['discount_percentage'],
            'quantity_discount': pricing['quantity_discount'],
        }
    
    @staticmethod
    def get_all_prices_for_product(product):
        """
        الحصول على كل أسعار المنتج من جميع قوائم الأسعار
        
        مفيد لعرض مقارنة الأسعار
        """
        from .models_price_list import PriceList, ProductVariantPrice, ProductVariant
        
        variant = ProductVariant.objects.filter(
            product=product
        ).select_related('family', 'size').first()
        
        prices = []
        
        for pl in PriceList.objects.filter(is_active=True).order_by('name'):
            price_data = {
                'price_list': pl,
                'list_name': pl.name,
                'list_type': pl.get_list_type_display(),
            }
            
            if variant:
                vp = ProductVariantPrice.objects.filter(
                    family=variant.family,
                    size=variant.size,
                    price_list=pl
                ).first()
                
                if vp:
                    price_data['unit_price'] = vp.effective_price
                    price_data['unit_price_with_tax'] = vp.final_price
                else:
                    base_price = variant.family.base_price * variant.size.price_multiplier
                    price_data['unit_price'] = pl.apply_discount(base_price)
                    price_data['unit_price_with_tax'] = pl.apply_tax(price_data['unit_price'])
            else:
                price_data['unit_price'] = pl.apply_discount(product.price)
                price_data['unit_price_with_tax'] = pl.apply_tax(price_data['unit_price'])
            
            prices.append(price_data)
        
        return prices


class TaxCalculationService:
    """خدمة حساب الضرائب"""
    
    @staticmethod
    def calculate_tax(amount: Decimal, tax_rate: Decimal) -> Decimal:
        """حساب مبلغ الضريبة"""
        return (amount * tax_rate / 100).quantize(Decimal('0.01'), ROUND_HALF_UP)
    
    @staticmethod
    def add_tax(amount: Decimal, tax_rate: Decimal) -> Decimal:
        """إضافة الضريبة للمبلغ"""
        return (amount * (1 + tax_rate / 100)).quantize(Decimal('0.01'), ROUND_HALF_UP)
    
    @staticmethod
    def remove_tax(amount_with_tax: Decimal, tax_rate: Decimal) -> Decimal:
        """إزالة الضريبة من المبلغ"""
        return (amount_with_tax / (1 + tax_rate / 100)).quantize(Decimal('0.01'), ROUND_HALF_UP)
    
    @staticmethod
    def get_tax_breakdown(amount: Decimal, tax_rate: Decimal, includes_tax: bool = False) -> Dict:
        """
        تفصيل الضريبة
        
        Args:
            amount: المبلغ
            tax_rate: نسبة الضريبة
            includes_tax: هل المبلغ شامل الضريبة
            
        Returns:
            {
                'amount_before_tax': المبلغ قبل الضريبة,
                'tax_amount': مبلغ الضريبة,
                'amount_with_tax': المبلغ شامل الضريبة,
                'tax_rate': نسبة الضريبة
            }
        """
        if includes_tax:
            amount_before_tax = TaxCalculationService.remove_tax(amount, tax_rate)
            tax_amount = amount - amount_before_tax
            amount_with_tax = amount
        else:
            amount_before_tax = amount
            tax_amount = TaxCalculationService.calculate_tax(amount, tax_rate)
            amount_with_tax = amount + tax_amount
        
        return {
            'amount_before_tax': amount_before_tax,
            'tax_amount': tax_amount,
            'amount_with_tax': amount_with_tax,
            'tax_rate': tax_rate,
        }
