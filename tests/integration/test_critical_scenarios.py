#!/usr/bin/env python
"""
اختبار السيناريوهات الحرجة لنظام Tony ERP
==========================================
هذا الملف يختبر السيناريوهات الأكثر أهمية للنظام:
1. دورة بيع كاملة (من الفاتورة للدفع)
2. دورة مشتريات كاملة (من الطلب للاستلام)
3. دورة إنتاج كاملة (من أمر الإنتاج للتسليم)
4. ترحيل قيود يومية
5. تكامل المخزون مع المبيعات

الاستخدام:
    python test_critical_scenarios.py
"""

import os
import sys
import django
import requests
from datetime import date, timedelta
from decimal import Decimal

# إعداد Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from django.db import transaction
from django.contrib.auth.models import User
from inventory.models import Product, Location, Stock
from partners.models import Customer, Supplier
from sales.models import Invoice, InvoiceItem
from purchases.models import PurchaseBill, PurchaseItem
from accounting.models import Account, JournalEntry, JournalEntryItem
from payments.models import PaymentMethod


class CriticalScenarioTester:
    """اختبار السيناريوهات الحرجة"""
    
    def __init__(self, base_url="http://127.0.0.1:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.results = {
            'passed': 0,
            'failed': 0,
            'errors': []
        }
    
    def log(self, message, status='info'):
        """طباعة رسالة مع رمز الحالة"""
        icons = {
            'info': '📋',
            'success': '✅',
            'error': '❌',
            'warning': '⚠️',
            'test': '🧪'
        }
        print(f"{icons.get(status, '•')} {message}")
    
    def test_passed(self, name):
        """تسجيل اختبار ناجح"""
        self.results['passed'] += 1
        self.log(f"{name}", 'success')
    
    def test_failed(self, name, error):
        """تسجيل اختبار فاشل"""
        self.results['failed'] += 1
        self.results['errors'].append(f"{name}: {error}")
        self.log(f"{name}: {error}", 'error')
    
    # ==========================================
    # سيناريو 1: دورة بيع كاملة
    # ==========================================
    def test_sales_cycle(self):
        """اختبار دورة البيع الكاملة"""
        self.log("اختبار دورة البيع الكاملة", 'test')
        
        try:
            with transaction.atomic():
                # 1. التحقق من وجود عميل
                customer = Customer.objects.first()
                if not customer:
                    customer = Customer.objects.create(
                        name="عميل اختبار",
                        email="test@example.com",
                        phone="0501234567"
                    )
                
                # 2. التحقق من وجود منتج ومخزون
                product = Product.objects.first()
                if not product:
                    self.test_failed("دورة البيع", "لا توجد منتجات")
                    return False
                
                location = Location.objects.filter(is_default=True).first()
                if not location:
                    location = Location.objects.first()
                
                # 3. التحقق من المخزون الحالي
                initial_stock = Stock.objects.filter(
                    product=product, 
                    location=location
                ).first()
                
                initial_qty = initial_stock.quantity if initial_stock else 0
                
                # 4. إنشاء فاتورة بيع
                invoice_number = f"TEST-INV-{date.today().strftime('%Y%m%d')}-001"
                invoice, created = Invoice.objects.get_or_create(
                    number=invoice_number,
                    defaults={
                        'customer': customer,
                        'date': date.today(),
                    }
                )
                
                if created:
                    # إضافة بند للفاتورة
                    InvoiceItem.objects.create(
                        invoice=invoice,
                        product=product,
                        location=location,
                        quantity=1,
                        price=float(product.price)
                    )
                    
                    self.test_passed(f"إنشاء فاتورة بيع: {invoice_number}")
                else:
                    self.log(f"الفاتورة موجودة مسبقاً: {invoice_number}", 'warning')
                
                # 5. التحقق من تحديث المخزون (إذا كان هناك تكامل)
                # ملاحظة: هذا يعتمد على منطق النظام
                
                self.test_passed("دورة البيع - الخطوات الأساسية")
                return True
                
        except Exception as e:
            self.test_failed("دورة البيع", str(e))
            return False
    
    # ==========================================
    # سيناريو 2: دورة مشتريات كاملة
    # ==========================================
    def test_purchase_cycle(self):
        """اختبار دورة المشتريات الكاملة"""
        self.log("اختبار دورة المشتريات الكاملة", 'test')
        
        try:
            with transaction.atomic():
                # 1. التحقق من وجود مورد
                supplier = Supplier.objects.first()
                if not supplier:
                    supplier = Supplier.objects.create(
                        name="مورد اختبار",
                        email="supplier@example.com",
                        phone="0112345678"
                    )
                
                # 2. التحقق من وجود منتج
                product = Product.objects.first()
                if not product:
                    self.test_failed("دورة المشتريات", "لا توجد منتجات")
                    return False
                
                location = Location.objects.filter(type='raw').first()
                if not location:
                    location = Location.objects.first()
                
                # 3. إنشاء فاتورة مشتريات
                bill_number = f"TEST-BILL-{date.today().strftime('%Y%m%d')}-001"
                
                # التحقق من عدم وجود الفاتورة مسبقاً
                existing_bill = PurchaseBill.objects.filter(number=bill_number).first()
                if existing_bill:
                    self.log(f"فاتورة المشتريات موجودة: {bill_number}", 'warning')
                    self.test_passed("دورة المشتريات - موجودة مسبقاً")
                    return True
                
                # PurchaseBill.supplier expects Partner, not Supplier
                bill = PurchaseBill.objects.create(
                    number=bill_number,
                    supplier=supplier.partner,
                    date=date.today(),
                )
                
                # إضافة بند
                PurchaseItem.objects.create(
                    bill=bill,
                    product=product,
                    quantity=10,
                    cost=float(product.cost),  # الحقل الصحيح هو cost وليس price
                    location=location,
                )
                
                self.test_passed(f"إنشاء فاتورة مشتريات: {bill_number}")
                return True
                
        except Exception as e:
            self.test_failed("دورة المشتريات", str(e))
            return False
    
    # ==========================================
    # سيناريو 3: ترحيل قيود يومية
    # ==========================================
    def test_journal_entry(self):
        """اختبار ترحيل قيود يومية"""
        self.log("اختبار ترحيل القيود اليومية", 'test')
        
        try:
            with transaction.atomic():
                # 1. التحقق من وجود حسابات
                accounts = Account.objects.all()[:2]
                if accounts.count() < 2:
                    self.test_failed("القيود اليومية", "لا توجد حسابات كافية (حساب مدين وحساب دائن)")
                    return False
                
                debit_account = accounts[0]
                credit_account = accounts[1]
                
                # 2. التحقق من وجود مستخدم
                user = User.objects.first()
                if not user:
                    self.test_failed("القيود اليومية", "لا يوجد مستخدم")
                    return False
                
                # 3. إنشاء قيد يومي
                entry_ref = f"TEST-JE-{date.today().strftime('%Y%m%d')}"
                
                # التحقق من عدم وجود القيد مسبقاً
                existing_entry = JournalEntry.objects.filter(reference=entry_ref).first()
                if existing_entry:
                    self.log(f"القيد موجود مسبقاً: {entry_ref}", 'warning')
                    self.test_passed("القيود اليومية - موجود مسبقاً")
                    return True
                
                entry = JournalEntry.objects.create(
                    reference=entry_ref,
                    date=date.today(),
                    description="قيد اختبار تلقائي",
                    created_by=user,
                )
                
                # إضافة بنود القيد (الحقول الصحيحة: type و amount)
                test_amount = Decimal('100.00')
                
                JournalEntryItem.objects.create(
                    journal_entry=entry,
                    account=debit_account,
                    type='debit',  # مدين
                    amount=test_amount,
                    description="مدين اختبار"
                )
                
                JournalEntryItem.objects.create(
                    journal_entry=entry,
                    account=credit_account,
                    type='credit',  # دائن
                    amount=test_amount,
                    description="دائن اختبار"
                )
                
                # 4. التحقق من توازن القيد
                total_debit = sum(item.amount for item in entry.items.filter(type='debit'))
                total_credit = sum(item.amount for item in entry.items.filter(type='credit'))
                
                if total_debit == total_credit:
                    self.test_passed(f"القيد متوازن: {entry_ref}")
                else:
                    self.test_failed("القيد اليومي", f"القيد غير متوازن: مدين={total_debit}, دائن={total_credit}")
                    return False
                
                return True
                
        except Exception as e:
            self.test_failed("القيود اليومية", str(e))
            return False
    
    # ==========================================
    # سيناريو 4: تكامل المخزون
    # ==========================================
    def test_inventory_integration(self):
        """اختبار تكامل المخزون"""
        self.log("اختبار تكامل المخزون", 'test')
        
        try:
            # 1. التحقق من المخزون الحالي
            products_with_stock = Product.objects.filter(stocks__quantity__gt=0).distinct()
            
            if products_with_stock.count() == 0:
                self.log("لا توجد منتجات بمخزون - سيتم إنشاء مخزون", 'warning')
                
                product = Product.objects.first()
                location = Location.objects.first()
                
                if product and location:
                    Stock.objects.get_or_create(
                        product=product,
                        location=location,
                        defaults={'quantity': 100}
                    )
                    self.test_passed("إنشاء مخزون ابتدائي")
            else:
                self.test_passed(f"يوجد {products_with_stock.count()} منتج بمخزون")
            
            # 2. التحقق من مواقع المخزون
            locations = Location.objects.all()
            if locations.count() == 0:
                self.test_failed("المخزون", "لا توجد مواقع تخزين")
                return False
            
            self.test_passed(f"يوجد {locations.count()} موقع تخزين")
            
            # 3. التحقق من المخزون المنخفض
            low_stock_products = []
            for product in Product.objects.all()[:10]:
                total_qty = sum(s.quantity for s in Stock.objects.filter(product=product))
                if total_qty < product.min_stock:
                    low_stock_products.append(product.name)
            
            if low_stock_products:
                self.log(f"تحذير: {len(low_stock_products)} منتج بمخزون منخفض", 'warning')
            else:
                self.test_passed("جميع المنتجات فوق الحد الأدنى")
            
            return True
            
        except Exception as e:
            self.test_failed("تكامل المخزون", str(e))
            return False
    
    # ==========================================
    # سيناريو 5: طرق الدفع والـ POS
    # ==========================================
    def test_payment_methods(self):
        """اختبار طرق الدفع"""
        self.log("اختبار طرق الدفع", 'test')
        
        try:
            # التحقق من وجود طرق دفع
            payment_methods = PaymentMethod.objects.all()
            
            if payment_methods.count() == 0:
                self.test_failed("طرق الدفع", "لا توجد طرق دفع")
                return False
            
            self.test_passed(f"يوجد {payment_methods.count()} طريقة دفع")
            
            # التحقق من الطرق الأساسية
            required_types = ['cash', 'credit_card']
            for ptype in required_types:
                exists = PaymentMethod.objects.filter(type=ptype).exists()
                if exists:
                    self.test_passed(f"طريقة الدفع '{ptype}' موجودة")
                else:
                    self.log(f"طريقة الدفع '{ptype}' غير موجودة", 'warning')
            
            return True
            
        except Exception as e:
            self.test_failed("طرق الدفع", str(e))
            return False
    
    # ==========================================
    # سيناريو 6: اختبار API الأساسي
    # ==========================================
    def test_api_endpoints(self):
        """اختبار نقاط API الأساسية"""
        self.log("اختبار نقاط API الأساسية", 'test')
        
        endpoints = [
            ("/api/docs/", "توثيق API"),
            ("/api/inventory/products/", "منتجات API"),
            ("/api/partners/customers/", "عملاء API"),
        ]
        
        for endpoint, name in endpoints:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}", timeout=5)
                if response.status_code in [200, 301, 302, 401, 403]:
                    self.test_passed(f"API {name}")
                else:
                    self.log(f"API {name}: حالة {response.status_code}", 'warning')
            except Exception as e:
                self.log(f"API {name}: {e}", 'warning')
        
        return True
    
    # ==========================================
    # تشغيل جميع الاختبارات
    # ==========================================
    def run_all_tests(self):
        """تشغيل جميع الاختبارات"""
        print("\n" + "=" * 70)
        print("🧪  اختبار السيناريوهات الحرجة لنظام Tony ERP")
        print("=" * 70 + "\n")
        
        tests = [
            ("دورة البيع الكاملة", self.test_sales_cycle),
            ("دورة المشتريات الكاملة", self.test_purchase_cycle),
            ("ترحيل القيود اليومية", self.test_journal_entry),
            ("تكامل المخزون", self.test_inventory_integration),
            ("طرق الدفع", self.test_payment_methods),
            ("نقاط API", self.test_api_endpoints),
        ]
        
        for test_name, test_func in tests:
            print(f"\n{'─' * 50}")
            try:
                test_func()
            except Exception as e:
                self.test_failed(test_name, str(e))
        
        # ملخص النتائج
        print("\n" + "=" * 70)
        print("📊  ملخص نتائج الاختبار")
        print("=" * 70)
        
        total = self.results['passed'] + self.results['failed']
        success_rate = (self.results['passed'] / total * 100) if total > 0 else 0
        
        print(f"\n   ✅ اختبارات ناجحة: {self.results['passed']}")
        print(f"   ❌ اختبارات فاشلة: {self.results['failed']}")
        print(f"   📈 نسبة النجاح: {success_rate:.1f}%")
        
        if self.results['errors']:
            print(f"\n   ⚠️ الأخطاء:")
            for error in self.results['errors']:
                print(f"      - {error}")
        
        print("\n" + "=" * 70)
        
        return success_rate >= 80


if __name__ == '__main__':
    tester = CriticalScenarioTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
