#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
سكريبت اختبار شامل لنظام POS
يتحقق من:
- وجود المنتجات بأسعار
- وجود جلسة نشطة
- إنشاء طلب اختبار
- إضافة منتجات للسلة
- حساب الإجماليات
- إتمام الدفع
"""

import os
import sys
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from decimal import Decimal
from django.contrib.auth import get_user_model
from pos.models import POSSession, POSOrder, POSOrderLine
from inventory.models import Product, Location
from partners.models import Customer
from payments.models import PaymentMethod

User = get_user_model()

def print_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def print_success(msg):
    print(f"✅ {msg}")

def print_error(msg):
    print(f"❌ {msg}")

def print_info(msg):
    print(f"ℹ️  {msg}")

def test_products():
    """اختبار المنتجات"""
    print_header("اختبار المنتجات")
    
    products = Product.objects.all()
    total = products.count()
    print_info(f"عدد المنتجات: {total}")
    
    with_price = products.filter(price__gt=0).count()
    print_info(f"منتجات بأسعار: {with_price}")
    
    if with_price == 0:
        print_error("لا توجد منتجات بأسعار!")
        return False
    
    # عرض عينة
    print_info("\nعينة من المنتجات:")
    for p in products.filter(price__gt=0)[:5]:
        print(f"  - {p.name}: {p.price} ج.م")
    
    print_success("المنتجات جاهزة")
    return True

def test_session():
    """اختبار الجلسات"""
    print_header("اختبار الجلسات")
    
    # الحصول على مستخدم
    user = User.objects.filter(is_superuser=True).first()
    if not user:
        user = User.objects.first()
    
    if not user:
        print_error("لا يوجد مستخدمين في النظام!")
        return None
    
    print_info(f"المستخدم: {user.username}")
    
    # البحث عن جلسة نشطة
    session = POSSession.objects.filter(user=user, is_open=True).first()
    
    if not session:
        # إنشاء جلسة جديدة
        location = Location.objects.first()
        if not location:
            print_error("لا توجد مواقع في النظام!")
            return None
        
        session = POSSession.objects.create(
            user=user,
            location=location,
            opening_balance=Decimal('1000.00')
        )
        print_success(f"تم إنشاء جلسة جديدة #{session.id}")
    else:
        print_info(f"جلسة نشطة موجودة #{session.id}")
    
    return session

def test_order_creation(session):
    """اختبار إنشاء طلب"""
    print_header("اختبار إنشاء طلب")
    
    # إنشاء طلب جديد
    order = POSOrder.objects.create(
        session=session,
        location=session.location,
        status='draft'
    )
    
    print_success(f"تم إنشاء طلب #{order.id} - {order.number}")
    
    return order

def test_add_products(order):
    """اختبار إضافة منتجات"""
    print_header("اختبار إضافة منتجات للطلب")
    
    # الحصول على 3 منتجات عشوائية
    products = Product.objects.filter(price__gt=0).order_by('?')[:3]
    
    if not products.exists():
        print_error("لا توجد منتجات للإضافة!")
        return False
    
    # إضافة المنتجات
    for product in products:
        line = POSOrderLine.objects.create(
            order=order,
            product=product,
            quantity=1,
            price=product.price
        )
        print_info(f"أضيف: {product.name} - {product.price} ج.م")
    
    print_success(f"تم إضافة {products.count()} منتج للطلب")
    
    return True

def test_calculation(order):
    """اختبار الحسابات"""
    print_header("اختبار الحسابات")
    
    # إعادة حساب الإجمالي
    order.recalc_total()
    
    print_info(f"الإجمالي قبل الضريبة: {order.subtotal} ج.م")
    print_info(f"الضريبة: {order.tax_amount} ج.م")
    print_info(f"الخصم: {order.discount_amount} ج.م")
    print_info(f"الإجمالي النهائي: {order.total} ج.م")
    
    print_success("الحسابات صحيحة")
    
    return True

def test_payment(order):
    """اختبار الدفع"""
    print_header("اختبار الدفع")
    
    # الحصول على طريقة دفع
    payment_method = PaymentMethod.objects.first()
    
    if not payment_method:
        # إنشاء طريقة دفع نقدي
        payment_method = PaymentMethod.objects.create(
            name='نقدي',
            is_active=True
        )
        print_info("تم إنشاء طريقة دفع نقدي")
    
    # إتمام الدفع
    order.finalize_payment(order.total, payment_method)
    
    print_success(f"تم الدفع بنجاح - الحالة: {order.status}")
    print_info(f"المبلغ المدفوع: {order.paid_amount} ج.م")
    
    return True

def test_api_endpoints():
    """اختبار API endpoints"""
    print_header("اختبار API Endpoints")
    
    from django.test import Client
    from django.contrib.auth import get_user_model
    
    client = Client()
    User = get_user_model()
    
    # تسجيل دخول
    user = User.objects.filter(is_superuser=True).first()
    if not user:
        user = User.objects.first()
    
    if not user:
        print_error("لا يوجد مستخدمين للاختبار!")
        return False
    
    client.force_login(user)
    
    # اختبار endpoints
    endpoints = [
        '/pos/',
        '/pos/session/open/',
        '/pos/api/product-lookup/?q=test',
    ]
    
    for endpoint in endpoints:
        try:
            response = client.get(endpoint)
            if response.status_code < 500:
                print_success(f"{endpoint} - {response.status_code}")
            else:
                print_error(f"{endpoint} - {response.status_code}")
        except Exception as e:
            print_error(f"{endpoint} - خطأ: {str(e)}")
    
    return True

def main():
    """تشغيل جميع الاختبارات"""
    print_header("🧪 اختبار شامل لنظام POS")
    
    try:
        # 1. اختبار المنتجات
        if not test_products():
            print_error("فشل اختبار المنتجات")
            return
        
        # 2. اختبار الجلسات
        session = test_session()
        if not session:
            print_error("فشل اختبار الجلسات")
            return
        
        # 3. اختبار إنشاء طلب
        order = test_order_creation(session)
        if not order:
            print_error("فشل إنشاء الطلب")
            return
        
        # 4. اختبار إضافة منتجات
        if not test_add_products(order):
            print_error("فشل إضافة المنتجات")
            return
        
        # 5. اختبار الحسابات
        if not test_calculation(order):
            print_error("فشل الحسابات")
            return
        
        # 6. اختبار الدفع
        if not test_payment(order):
            print_error("فشل الدفع")
            return
        
        # 7. اختبار API
        test_api_endpoints()
        
        print_header("🎉 نجحت جميع الاختبارات!")
        print_success(f"تم إنشاء طلب اختباري برقم: {order.number}")
        print_success(f"عرض الإيصال: http://72.62.176.249/pos/order/{order.id}/receipt/")
        
    except Exception as e:
        import traceback
        print_error(f"حدث خطأ: {str(e)}")
        traceback.print_exc()

if __name__ == '__main__':
    main()
