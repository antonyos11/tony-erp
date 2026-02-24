#!/usr/bin/env python3
"""
سكريبت لإعداد بيانات المتجر الإلكتروني
Setup Store Demo Data
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from ecommerce.models import *
from django.contrib.auth import get_user_model
from decimal import Decimal

User = get_user_model()

def setup_store_settings():
    """إعداد إعدادات المتجر"""
    print("🏪 إعداد إعدادات المتجر...")
    settings = EcommerceSettings.get_settings()
    settings.store_name = "Tony Store"
    settings.store_description = "متجر إلكتروني متكامل لبيع المنتجات عالية الجودة"
    settings.contact_email = "info@tonystore.com"
    settings.contact_phone = "966XXXXXXXXX"
    settings.whatsapp_number = "966XXXXXXXXX"
    settings.free_shipping_threshold = Decimal('500.00')
    settings.default_shipping_cost = Decimal('50.00')
    settings.is_active = True
    settings.save()
    print(f"✅ تم تحديث إعدادات المتجر: {settings.store_name}")
    return settings

def setup_payment_gateways():
    """إعداد بوابات الدفع"""
    print("\n💳 إعداد بوابات الدفع...")
    
    gateways = [
        {
            'name': 'الدفع عند الاستلام',
            'gateway_type': 'cod',
            'is_active': True,
            'sort_order': 1
        },
        {
            'name': 'تحويل بنكي',
            'gateway_type': 'bank_transfer',
            'is_active': True,
            'sort_order': 2
        }
    ]
    
    created_count = 0
    for gw_data in gateways:
        gateway, created = PaymentGateway.objects.get_or_create(
            gateway_type=gw_data['gateway_type'],
            defaults=gw_data
        )
        if created:
            created_count += 1
            print(f"   ✓ {gateway.name}")
    
    print(f"✅ تم إنشاء {created_count} بوابة دفع جديدة")
    return PaymentGateway.objects.count()

def setup_shipping_companies():
    """إعداد شركات الشحن"""
    print("\n🚚 إعداد شركات الشحن...")
    
    companies = [
        {
            'name': 'SMSA',
            'tracking_url': 'https://www.smsaexpress.com/trackshipment',
            'is_active': True,
            'sort_order': 1
        },
        {
            'name': 'Aramex',
            'tracking_url': 'https://www.aramex.com/track/results',
            'is_active': True,
            'sort_order': 2
        },
        {
            'name': 'DHL',
            'tracking_url': 'https://www.dhl.com/sa-en/home/tracking.html',
            'is_active': True,
            'sort_order': 3
        }
    ]
    
    created_count = 0
    for company_data in companies:
        company, created = ShippingCompany.objects.get_or_create(
            name=company_data['name'],
            defaults=company_data
        )
        if created:
            created_count += 1
            print(f"   ✓ {company.name}")
    
    print(f"✅ تم إنشاء {created_count} شركة شحن جديدة")
    return ShippingCompany.objects.count()

def setup_banners():
    """إعداد البانرات"""
    print("\n🎨 إعداد البانرات...")
    
    banners = [
        {
            'title': 'عروض خاصة',
            'subtitle': 'خصومات تصل إلى 50%',
            'button_text': 'تسوق الآن',
            'link_url': 'http://72.62.176.240/ecommerce/products/',
            'position': 'home_slider',
            'is_active': True,
            'sort_order': 1
        },
        {
            'title': 'منتجات جديدة',
            'subtitle': 'اكتشف أحدث المنتجات',
            'button_text': 'استكشف',
            'link_url': 'http://72.62.176.240/ecommerce/products/',
            'position': 'home_slider',
            'is_active': True,
            'sort_order': 2
        }
    ]
    
    created_count = 0
    try:
        for banner_data in banners:
            # إزالة الحقل image لأنه مطلوب لكن ليس لدينا صورة حقيقية
            # سنتجاوز إنشاء البانرات لأنها تحتاج صور
            pass
        print(f"⚠️ تم تخطي البانرات (تحتاج صور)")
    except Exception as e:
        print(f"⚠️ {e}")
    
    return StoreBanner.objects.count()

def setup_page_content():
    """إعداد محتوى الصفحات"""
    print("\n📄 إعداد محتوى الصفحات...")
    
    pages = {
        'about': {
            'title': 'من نحن',
            'content': '''
            <h2>مرحباً بكم في Tony Store</h2>
            <p>نحن متجر إلكتروني متخصص في تقديم أفضل المنتجات بأعلى جودة وأفضل الأسعار.</p>
            <p>نهدف لتقديم تجربة تسوق مميزة لعملائنا الكرام.</p>
            '''
        },
        'terms': {
            'title': 'الشروط والأحكام',
            'content': '''
            <h2>شروط وأحكام الاستخدام</h2>
            <p>باستخدامك لهذا الموقع، فإنك توافق على الشروط والأحكام التالية...</p>
            '''
        },
        'privacy': {
            'title': 'سياسة الخصوصية',
            'content': '''
            <h2>سياسة الخصوصية</h2>
            <p>نحن نحترم خصوصيتك ونلتزم بحماية بياناتك الشخصية...</p>
            '''
        },
        'shipping': {
            'title': 'الشحن والتوصيل',
            'content': '''
            <h2>سياسة الشحن والتوصيل</h2>
            <p>نوفر خدمة التوصيل لجميع مناطق المملكة...</p>
            <ul>
                <li>التوصيل المجاني للطلبات فوق 500 ج.م</li>
                <li>مدة التوصيل: 2-5 أيام عمل</li>
                <li>إمكانية تتبع الشحنة</li>
            </ul>
            '''
        }
    }
    
    created_count = 0
    for page_key, page_data in pages.items():
        page, created = StorePageContent.objects.get_or_create(
            page=page_key,
            defaults=page_data
        )
        if created:
            created_count += 1
            print(f"   ✓ {page.title}")
    
    print(f"✅ تم إنشاء {created_count} صفحة جديدة")
    return StorePageContent.objects.count()

def create_sample_order():
    """إنشاء طلب تجريبي"""
    print("\n🛒 إنشاء طلب تجريبي...")
    
    try:
        # الحصول على عميل
        customer = Customer.objects.first()
        if not customer:
            user = User.objects.filter(is_superuser=False).first()
            if not user:
                user = User.objects.create_user(
                    username='customer1',
                    email='customer@test.com',
                    password='test123'
                )
            customer = Customer.objects.create(
                user=user,
                phone='0501234567'
            )
        
        # الحصول على منتج
        product = OnlineProduct.objects.filter(is_active=True).first()
        if not product:
            print("⚠️ لا توجد منتجات متاحة")
            return None
        
        # إنشاء الطلب
        order = Order.objects.create(
            customer=customer,
            customer_name=customer.user.get_full_name() or customer.user.username,
            customer_email=customer.user.email,
            customer_phone=customer.phone,
            shipping_address='الرياض، المملكة العربية مصر',
            status='pending',
            subtotal=Decimal('100.00'),
            shipping_cost=Decimal('50.00'),
            tax=Decimal('15.00'),
            total=Decimal('165.00')
        )
        
        # إضافة عنصر للطلب
        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=1,
            unit_price=Decimal('100.00'),
            total=Decimal('100.00')
        )
        
        print(f"✅ تم إنشاء طلب تجريبي: {order.order_number}")
        return order
    except Exception as e:
        print(f"❌ خطأ في إنشاء الطلب: {e}")
        return None

def main():
    """تشغيل جميع عمليات الإعداد"""
    print("=" * 60)
    print("🚀 إعداد بيانات المتجر الإلكتروني")
    print("=" * 60)
    
    try:
        # 1. إعدادات المتجر
        setup_store_settings()
        
        # 2. بوابات الدفع
        setup_payment_gateways()
        
        # 3. شركات الشحن
        setup_shipping_companies()
        
        # 4. البانرات
        setup_banners()
        
        # 5. محتوى الصفحات
        setup_page_content()
        
        # 6. طلب تجريبي
        create_sample_order()
        
        print("\n" + "=" * 60)
        print("✅ اكتمل إعداد المتجر بنجاح!")
        print("=" * 60)
        print("\n📊 الإحصائيات النهائية:")
        print(f"   - المنتجات: {OnlineProduct.objects.count()}")
        print(f"   - العملاء: {Customer.objects.count()}")
        print(f"   - الطلبات: {Order.objects.count()}")
        print(f"   - بوابات الدفع: {PaymentGateway.objects.count()}")
        print(f"   - شركات الشحن: {ShippingCompany.objects.count()}")
        print(f"   - البانرات: {StoreBanner.objects.count()}")
        print(f"   - الصفحات: {StorePageContent.objects.count()}")
        print("\n🌐 رابط المتجر: http://72.62.176.240/ecommerce/")
        
    except Exception as e:
        print(f"\n❌ حدث خطأ: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
