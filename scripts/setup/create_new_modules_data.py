#!/usr/bin/env python3
"""
إنشاء بيانات اختبارية للوحدات الجديدة
- smart_pricing
- subscriptions
- zatca_integration
"""

import os
import sys
import django
from decimal import Decimal

# Setup Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from django.contrib.auth import get_user_model
from smart_pricing.models import PricingRule, SmartQuote, ProductionLineRecommendation
from subscriptions.models import SubscriptionPlan, CustomerSubscription
from zatca_integration.models import ZATCAConfiguration
from core.models import Company
from inventory.models import Product, Location

User = get_user_model()


def create_smart_pricing_data():
    """إنشاء بيانات التسعير الذكي"""
    print("✓ إنشاء بيانات التسعير الذكي...")
    
    # قاعدة تسعير للأثاث المخصص
    rule1, created = PricingRule.objects.get_or_create(
        name='تسعير الأثاث المخصص',
        defaults={
            'product_category': 'أثاث',
            'method': 'ai_dynamic',
            'base_cost_multiplier': Decimal('1.5'),
            'quantity_discount_threshold': 50,
            'quantity_discount_rate': Decimal('10.0'),
            'min_profit_margin': Decimal('20.0'),
            'target_profit_margin': Decimal('35.0'),
            'max_profit_margin': Decimal('50.0'),
            'use_ai_pricing': True,
            'is_active': True,
        }
    )
    if created:
        print(f"  - تم إنشاء قاعدة: {rule1.name}")
    
    # قاعدة تسعير للمعادن
    rule2, created = PricingRule.objects.get_or_create(
        name='تسعير المنتجات المعدنية',
        defaults={
            'product_category': 'معادن',
            'method': 'cost_plus',
            'base_cost_multiplier': Decimal('1.3'),
            'quantity_discount_threshold': 100,
            'quantity_discount_rate': Decimal('15.0'),
            'min_profit_margin': Decimal('15.0'),
            'target_profit_margin': Decimal('25.0'),
            'max_profit_margin': Decimal('40.0'),
            'is_active': True,
        }
    )
    if created:
        print(f"  - تم إنشاء قاعدة: {rule2.name}")
    
    return rule1, rule2


def create_subscription_plans():
    """إنشاء خطط الاشتراكات"""
    print("\n✓ إنشاء خطط الاشتراكات...")
    
    plans_data = [
        {
            'name': 'باقة البداية',
            'code': 'starter-2026',
            'plan_type': 'starter',
            'description': 'باقة مثالية للشركات الناشئة والصغيرة',
            'monthly_price': Decimal('299.00'),
            'annual_price': Decimal('3000.00'),
            'max_users': 5,
            'max_products': 500,
            'max_invoices_per_month': 100,
            'max_storage_gb': 10,
            'features': ['تقارير أساسية', 'دعم بريد إلكتروني', 'مستخدمين محدودين'],
            'is_active': True,
        },
        {
            'name': 'باقة الأعمال',
            'code': 'business-2026',
            'plan_type': 'business',
            'description': 'باقة شاملة للشركات المتوسطة',
            'monthly_price': Decimal('599.00'),
            'quarterly_price': Decimal('1699.00'),
            'annual_price': Decimal('6500.00'),
            'max_users': 20,
            'max_products': 5000,
            'max_invoices_per_month': 500,
            'max_storage_gb': 50,
            'features': ['تقارير متقدمة', 'دعم هاتفي', 'مستخدمين غير محدودين', 'تكامل API'],
            'has_api_access': True,
            'has_advanced_reports': True,
            'is_active': True,
        },
        {
            'name': 'باقة المؤسسات',
            'code': 'enterprise-2026',
            'plan_type': 'enterprise',
            'description': 'حلول متكاملة للمؤسسات الكبيرة',
            'monthly_price': Decimal('1999.00'),
            'annual_price': Decimal('21999.00'),
            'max_users': 0,  # غير محدود
            'max_products': 0,  # غير محدود
            'max_invoices_per_month': 0,  # غير محدود
            'max_storage_gb': 500,
            'features': ['كل المزايا', 'دعم مخصص 24/7', 'استشارات مجانية', 'تدريب', 'تخصيص كامل'],
            'has_api_access': True,
            'has_mobile_app': True,
            'has_advanced_reports': True,
            'has_ai_features': True,
            'has_whatsapp_integration': True,
            'has_ecommerce': True,
            'has_multi_branch': True,
            'has_priority_support': True,
            'is_active': True,
            'is_featured': True,
        },
    ]
    
    created_plans = []
    for plan_data in plans_data:
        plan, created = SubscriptionPlan.objects.get_or_create(
            code=plan_data['code'],
            defaults=plan_data
        )
        if created:
            print(f"  - تم إنشاء باقة: {plan.name} - {plan.monthly_price} ج.م/شهر")
        created_plans.append(plan)
    
    return created_plans


def create_zatca_config():
    """إنشاء إعدادات ZATCA"""
    print("\n✓ إنشاء إعدادات ZATCA للفوترة الإلكترونية...")
    
    # البحث عن أو إنشاء شركة
    company = Company.objects.first()
    if not company:
        company = Company.objects.create(
            name='شركة توني للأنظمة',
            tax_id='300000000000003',
            commercial_register='1010000000',
            address='الرياض، المملكة العربية مصر',
            phone='+966123456789',
            email='info@tonyerp.com',
            website='https://tonyerp.com',
        )
        print(f"  - تم إنشاء شركة: {company.name}")
    
    # إنشاء إعدادات ZATCA
    config, created = ZATCAConfiguration.objects.get_or_create(
        company=company,
        defaults={
            'vat_number': '300000000000003',
            'crn': '1010000000',
            'environment': 'sandbox',
            'api_base_url': 'https://gw-fatoora.zatca.gov.sa/e-invoicing/developer-portal',
            'seller_name': company.name,
            'building_number': '1234',
            'street_name': 'شارع الملك فهد',
            'district': 'العليا',
            'city': 'الرياض',
            'postal_code': '12345',
            'is_active': True,
        }
    )
    
    if created:
        print(f"  - تم إنشاء إعدادات ZATCA للشركة: {company.name}")
        print(f"  - البيئة: {config.get_environment_display()}")
        print(f"  - الرقم الضريبي: {config.vat_number}")
    
    return config


def main():
    print("\n" + "="*60)
    print("إنشاء بيانات اختبارية للوحدات الجديدة")
    print("="*60 + "\n")
    
    try:
        # 1. التسعير الذكي
        rules = create_smart_pricing_data()
        
        # 2. خطط الاشتراكات
        plans = create_subscription_plans()
        
        # 3. إعدادات ZATCA
        zatca_config = create_zatca_config()
        
        print("\n" + "="*60)
        print("✅ تم إنشاء جميع البيانات بنجاح!")
        print("="*60)
        print("\nالملخص:")
        print(f"  - قواعد التسعير الذكي: {PricingRule.objects.count()}")
        print(f"  - خطط الاشتراكات: {SubscriptionPlan.objects.count()}")
        print(f"  - إعدادات ZATCA: {ZATCAConfiguration.objects.count()}")
        print("\nيمكنك الآن:")
        print("  1. الدخول إلى لوحة الإدارة: /admin/")
        print("  2. عرض التسعير الذكي: /admin/smart_pricing/")
        print("  3. إدارة الاشتراكات: /admin/subscriptions/")
        print("  4. إعدادات ZATCA: /admin/zatca_integration/")
        print()
        
    except Exception as e:
        print(f"\n❌ خطأ: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
