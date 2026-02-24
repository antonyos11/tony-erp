# -*- coding: utf-8 -*-
"""
خدمة حساب التكاليف - Cost Calculation Service
=============================================
خدمة ذكية لحساب وتحديث تكاليف المنتجات تلقائياً عند تغير أسعار المواد الخام

الميزات:
- حساب تكلفة المنتج من قائمة المواد (BOM)
- تحديث تكاليف جميع المنتجات المتأثرة عند تغير سعر مادة خام
- دعم التحديث الجماعي (Bulk Update) للأداء العالي
- تسجيل تاريخ التكاليف
- حساب تأثير تغير السعر على الأرباح
"""

from decimal import Decimal
from typing import List, Dict, Optional, Tuple
from django.db import transaction
from django.db.models import Sum, F, Q
from django.utils import timezone
from django.contrib.auth.models import User
import logging

logger = logging.getLogger(__name__)


class CostCalculationService:
    """
    خدمة حساب التكاليف الذكية
    """
    
    def __init__(self, user: Optional[User] = None):
        self.user = user
        self._cache = {}
    
    def calculate_product_cost_from_bom(self, product_id: int, bom_id: Optional[int] = None) -> Dict:
        """
        حساب تكلفة منتج من قائمة المواد (BOM)
        
        Args:
            product_id: معرف المنتج
            bom_id: معرف قائمة المواد (اختياري - يستخدم الافتراضي)
        
        Returns:
            dict: تفاصيل التكلفة
        """
        from inventory.models import Product
        from production.models import BillOfMaterials, BOMItem
        
        try:
            product = Product.objects.get(pk=product_id)
            
            # جلب قائمة المواد
            if bom_id:
                bom = BillOfMaterials.objects.get(pk=bom_id, product=product)
            else:
                bom = BillOfMaterials.objects.filter(
                    product=product, 
                    is_active=True, 
                    is_default=True
                ).first()
            
            if not bom:
                return {
                    'success': False,
                    'error': 'لا توجد قائمة مواد للمنتج',
                    'product_id': product_id,
                }
            
            # حساب تكلفة المواد
            material_cost = Decimal('0')
            material_details = []
            
            for item in bom.items.select_related('material').all():
                # جلب تكلفة المادة الخام
                material = item.material
                
                # استخدام تكلفة وحدة الاستخدام
                unit_cost = material.usage_unit_cost or material.cost or Decimal('0')
                
                # حساب الكمية مع الهدر
                qty_with_wastage = item.quantity * (1 + (item.wastage_percentage or Decimal('0')) / 100)
                
                # حساب التكلفة
                item_cost = qty_with_wastage * unit_cost
                material_cost += item_cost
                
                material_details.append({
                    'material_id': material.id,
                    'material_name': material.name,
                    'quantity': float(item.quantity),
                    'wastage_percentage': float(item.wastage_percentage or 0),
                    'quantity_with_wastage': float(qty_with_wastage),
                    'unit_cost': float(unit_cost),
                    'total_cost': float(item_cost),
                })
            
            # حساب تكلفة العمالة والتكاليف الإضافية من BOM
            labor_cost = bom.total_labor_cost or Decimal('0')
            overhead_cost = bom.total_overhead_cost or Decimal('0')
            
            # إجمالي التكلفة
            total_cost = material_cost + labor_cost + overhead_cost
            
            # تكلفة الوحدة (مقسومة على الكمية الأساسية)
            base_qty = bom.base_quantity or Decimal('1')
            unit_total_cost = total_cost / base_qty
            
            return {
                'success': True,
                'product_id': product_id,
                'product_name': product.name,
                'bom_id': bom.id,
                'bom_version': bom.version,
                'base_quantity': float(base_qty),
                'material_cost': float(material_cost),
                'labor_cost': float(labor_cost),
                'overhead_cost': float(overhead_cost),
                'total_cost': float(total_cost),
                'unit_cost': float(unit_total_cost),
                'material_details': material_details,
                'calculated_at': timezone.now().isoformat(),
            }
            
        except Product.DoesNotExist:
            return {
                'success': False,
                'error': 'المنتج غير موجود',
                'product_id': product_id,
            }
        except Exception as e:
            logger.error(f"Error calculating cost for product {product_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'product_id': product_id,
            }
    
    def get_products_using_material(self, material_id: int) -> List[Dict]:
        """
        جلب جميع المنتجات التي تستخدم مادة خام معينة
        
        Args:
            material_id: معرف المادة الخام
        
        Returns:
            قائمة المنتجات مع تفاصيل الاستخدام
        """
        from production.models import BOMItem, BillOfMaterials
        
        # جلب جميع عناصر BOM التي تستخدم هذه المادة
        bom_items = BOMItem.objects.filter(
            material_id=material_id,
            bom__is_active=True
        ).select_related('bom', 'bom__product')
        
        products = []
        seen_products = set()
        
        for item in bom_items:
            product = item.bom.product
            if product.id not in seen_products:
                seen_products.add(product.id)
                products.append({
                    'product_id': product.id,
                    'product_name': product.name,
                    'product_sku': product.sku,
                    'bom_id': item.bom.id,
                    'bom_version': item.bom.version,
                    'quantity_used': float(item.quantity),
                    'wastage_percentage': float(item.wastage_percentage or 0),
                })
        
        return products
    
    @transaction.atomic
    def update_costs_for_material_price_change(
        self,
        material_id: int,
        old_price: Decimal,
        new_price: Decimal,
        price_history_id: Optional[int] = None,
        update_selling_price: bool = False,
        maintain_margin: bool = False
    ) -> Dict:
        """
        تحديث تكاليف جميع المنتجات المتأثرة بتغير سعر مادة خام
        
        Args:
            material_id: معرف المادة الخام
            old_price: السعر القديم
            new_price: السعر الجديد
            price_history_id: معرف سجل تغيير السعر
            update_selling_price: هل يتم تحديث سعر البيع تلقائياً؟
            maintain_margin: هل يتم الحفاظ على هامش الربح؟
        
        Returns:
            dict: نتائج التحديث
        """
        from inventory.models import Product
        from production.models import BillOfMaterials
        from .price_history import MaterialPriceHistory, ProductCostHistory, PriceChangeImpact
        
        results = {
            'success': True,
            'material_id': material_id,
            'old_price': float(old_price),
            'new_price': float(new_price),
            'price_change': float(new_price - old_price),
            'affected_products': [],
            'total_affected': 0,
            'errors': [],
        }
        
        # جلب المادة الخام
        try:
            material = Product.objects.get(pk=material_id)
        except Product.DoesNotExist:
            results['success'] = False
            results['errors'].append('المادة الخام غير موجودة')
            return results
        
        # جلب سجل تغيير السعر
        price_history = None
        if price_history_id:
            try:
                price_history = MaterialPriceHistory.objects.get(pk=price_history_id)
            except MaterialPriceHistory.DoesNotExist:
                pass
        
        # جلب جميع المنتجات المتأثرة
        affected_products = self.get_products_using_material(material_id)
        results['total_affected'] = len(affected_products)
        
        for product_data in affected_products:
            product_id = product_data['product_id']
            
            try:
                product = Product.objects.get(pk=product_id)
                
                # حفظ التكلفة القديمة
                old_cost = product.cost or Decimal('0')
                old_price_product = product.price or Decimal('0')
                
                # حساب التكلفة الجديدة
                cost_result = self.calculate_product_cost_from_bom(product_id)
                
                if cost_result['success']:
                    new_cost = Decimal(str(cost_result['unit_cost']))
                    
                    # تحديث تكلفة المنتج
                    product.cost = new_cost
                    
                    # تحديث سعر البيع إذا مطلوب
                    new_selling_price = old_price_product
                    if update_selling_price and maintain_margin and old_cost > 0:
                        # حساب هامش الربح القديم
                        old_margin_percent = ((old_price_product - old_cost) / old_cost * 100)
                        # تطبيق نفس الهامش على التكلفة الجديدة
                        new_selling_price = new_cost * (1 + old_margin_percent / 100)
                        product.price = new_selling_price.quantize(Decimal('0.01'))
                    
                    product.save(update_fields=['cost', 'price'] if update_selling_price else ['cost'])
                    
                    # تحديث BOM
                    bom = BillOfMaterials.objects.filter(
                        product_id=product_id, 
                        is_active=True, 
                        is_default=True
                    ).first()
                    
                    if bom:
                        bom.total_material_cost = Decimal(str(cost_result['material_cost']))
                        bom.save(update_fields=['total_material_cost'])
                    
                    # حساب هامش الربح
                    old_margin = float((old_price_product - old_cost) / old_price_product * 100) if old_price_product > 0 else 0
                    new_margin = float((new_selling_price - new_cost) / new_selling_price * 100) if new_selling_price > 0 else 0
                    
                    # تسجيل تاريخ التكلفة
                    ProductCostHistory.objects.create(
                        product=product,
                        bom=bom,
                        old_material_cost=Decimal(str(cost_result.get('old_material_cost', 0) or 0)),
                        new_material_cost=Decimal(str(cost_result['material_cost'])),
                        old_total_cost=old_cost,
                        new_total_cost=new_cost,
                        triggered_by=price_history,
                        changed_by=self.user,
                        notes=f"تحديث تلقائي بسبب تغير سعر: {material.name}"
                    )
                    
                    # تسجيل تأثير التغيير
                    if price_history:
                        qty_used = Decimal(str(product_data['quantity_used']))
                        unit_impact = (new_price - old_price) * qty_used
                        
                        # حساب تأثير المخزون
                        current_stock = product.current_stock or 0
                        stock_impact = unit_impact * current_stock
                        
                        PriceChangeImpact.objects.create(
                            price_change=price_history,
                            affected_product=product,
                            quantity_used=qty_used,
                            unit_cost_impact=unit_impact,
                            old_profit_margin=Decimal(str(old_margin)),
                            new_profit_margin=Decimal(str(new_margin)),
                            current_stock=Decimal(str(current_stock)),
                            stock_value_impact=stock_impact,
                        )
                    
                    results['affected_products'].append({
                        'product_id': product_id,
                        'product_name': product.name,
                        'old_cost': float(old_cost),
                        'new_cost': float(new_cost),
                        'cost_change': float(new_cost - old_cost),
                        'old_margin': old_margin,
                        'new_margin': new_margin,
                        'updated': True,
                    })
                else:
                    results['errors'].append(f"خطأ في حساب تكلفة {product.name}: {cost_result.get('error')}")
                    
            except Exception as e:
                logger.error(f"Error updating product {product_id}: {e}")
                results['errors'].append(f"خطأ في تحديث المنتج {product_id}: {str(e)}")
        
        return results
    
    def calculate_price_change_impact(
        self,
        material_id: int,
        old_price: Decimal,
        new_price: Decimal
    ) -> Dict:
        """
        حساب تأثير تغيير السعر قبل تطبيقه (للمعاينة)
        
        Args:
            material_id: معرف المادة الخام
            old_price: السعر القديم
            new_price: السعر الجديد
        
        Returns:
            dict: تحليل التأثير
        """
        from inventory.models import Product
        
        results = {
            'material_id': material_id,
            'old_price': float(old_price),
            'new_price': float(new_price),
            'price_change': float(new_price - old_price),
            'change_percentage': 0,
            'affected_products': [],
            'summary': {
                'total_products': 0,
                'total_cost_increase': 0,
                'total_cost_decrease': 0,
                'total_stock_value_impact': 0,
                'avg_margin_change': 0,
            }
        }
        
        # حساب نسبة التغيير
        if old_price > 0:
            results['change_percentage'] = float((new_price - old_price) / old_price * 100)
        
        # جلب المنتجات المتأثرة
        affected_products = self.get_products_using_material(material_id)
        results['summary']['total_products'] = len(affected_products)
        
        total_cost_change = Decimal('0')
        total_stock_impact = Decimal('0')
        margin_changes = []
        
        for product_data in affected_products:
            try:
                product = Product.objects.get(pk=product_data['product_id'])
                
                qty_used = Decimal(str(product_data['quantity_used']))
                wastage = Decimal(str(product_data.get('wastage_percentage', 0) or 0))
                qty_with_wastage = qty_used * (1 + wastage / 100)
                
                # حساب تأثير تكلفة الوحدة
                old_cost_component = old_price * qty_with_wastage
                new_cost_component = new_price * qty_with_wastage
                unit_cost_impact = new_cost_component - old_cost_component
                
                total_cost_change += unit_cost_impact
                
                # حساب تأثير المخزون
                current_stock = Decimal(str(product.current_stock or 0))
                stock_impact = unit_cost_impact * current_stock
                total_stock_impact += stock_impact
                
                # حساب تأثير هامش الربح
                current_cost = product.cost or Decimal('0')
                current_price = product.price or Decimal('0')
                
                old_margin = float((current_price - current_cost) / current_price * 100) if current_price > 0 else 0
                new_cost = current_cost + unit_cost_impact
                new_margin = float((current_price - new_cost) / current_price * 100) if current_price > 0 else 0
                
                margin_change = new_margin - old_margin
                margin_changes.append(margin_change)
                
                results['affected_products'].append({
                    'product_id': product.id,
                    'product_name': product.name,
                    'product_sku': product.sku,
                    'quantity_used': float(qty_with_wastage),
                    'current_cost': float(current_cost),
                    'new_cost': float(new_cost),
                    'unit_cost_impact': float(unit_cost_impact),
                    'current_stock': float(current_stock),
                    'stock_value_impact': float(stock_impact),
                    'old_margin': old_margin,
                    'new_margin': new_margin,
                    'margin_change': margin_change,
                })
                
            except Product.DoesNotExist:
                continue
            except Exception as e:
                logger.error(f"Error calculating impact for product {product_data['product_id']}: {e}")
        
        # ملخص
        if total_cost_change > 0:
            results['summary']['total_cost_increase'] = float(total_cost_change)
        else:
            results['summary']['total_cost_decrease'] = float(abs(total_cost_change))
        
        results['summary']['total_stock_value_impact'] = float(total_stock_impact)
        
        if margin_changes:
            results['summary']['avg_margin_change'] = sum(margin_changes) / len(margin_changes)
        
        return results
    
    @transaction.atomic
    def recalculate_all_bom_costs(self) -> Dict:
        """
        إعادة حساب تكاليف جميع قوائم المواد
        يستخدم للتحديث الدوري أو بعد تحديثات جماعية
        """
        from production.models import BillOfMaterials
        
        results = {
            'success': True,
            'total_processed': 0,
            'updated': 0,
            'errors': [],
        }
        
        boms = BillOfMaterials.objects.filter(is_active=True).select_related('product')
        
        for bom in boms:
            results['total_processed'] += 1
            
            try:
                cost_result = self.calculate_product_cost_from_bom(bom.product_id, bom.id)
                
                if cost_result['success']:
                    # تحديث BOM
                    bom.total_material_cost = Decimal(str(cost_result['material_cost']))
                    bom.save(update_fields=['total_material_cost', 'updated_at'])
                    
                    # تحديث المنتج
                    product = bom.product
                    product.cost = Decimal(str(cost_result['unit_cost']))
                    product.save(update_fields=['cost'])
                    
                    results['updated'] += 1
                else:
                    results['errors'].append(f"BOM {bom.id}: {cost_result.get('error')}")
                    
            except Exception as e:
                results['errors'].append(f"BOM {bom.id}: {str(e)}")
        
        return results


def get_cost_service(user: Optional[User] = None) -> CostCalculationService:
    """
    Factory function للحصول على خدمة حساب التكاليف
    """
    return CostCalculationService(user=user)
