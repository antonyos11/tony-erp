#!/usr/bin/env python
"""
إنشاء بيانات تجريبية بسيطة بدون مشاكل المخزون
"""

import os
import sys
import django
from datetime import date, timedelta
from decimal import Decimal

# إعداد Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from inventory.models import Product, Location
from partners.models import Customer, Supplier
from hr.models import Department, JobPosition, Employee
from crm.models import Customer as CRMCustomer, OpportunityStage
from sales.models import Invoice, InvoiceItem
from django.contrib.auth.models import User

def create_simple_data():
    """إنشاء بيانات تجريبية بسيطة"""
    
    print("بدء إنشاء بيانات تجريبية بسيطة...")
    
    # 1. إنشاء مواقع بسيطة
    print("إنشاء المواقع...")
    main_location, _ = Location.objects.get_or_create(
        code='MAIN',
        defaults={
            'name': 'المخزن الرئيسي',
            'type': 'other',
            'is_default': True
        }
    )
    
    # 2. إنشاء منتجات بدون مخزون
    print("إنشاء المنتجات...")
    products_data = [
        ('MAT-001', 'مرتبة طبية مفردة', 1500.00, 900.00, 'unit'),
        ('MAT-002', 'مرتبة سوست زوجي', 2500.00, 1500.00, 'unit'),
        ('PIL-001', 'وسادة طبية', 150.00, 80.00, 'unit'),
        ('FOA-001', 'إسفنج عالي الكثافة', 25.00, 15.00, 'm'),
        ('FAB-001', 'قماش قطني', 45.00, 30.00, 'm'),
    ]
    
    for sku, name, price, cost, uom in products_data:
        Product.objects.get_or_create(
            sku=sku,
            defaults={
                'name': name,
                'price': Decimal(str(price)),
                'cost': Decimal(str(cost)),
                'purchase_uom': uom,
                'usage_uom': uom,
                'min_stock': 10
            }
        )
    
    # 3. إنشاء عملاء
    print("إنشاء العملاء...")
    customers_data = [
        ('أحمد محمد', 'ahmed@example.com', '0501234567'),
        ('شركة النور للأثاث', 'info@alnoor.com', '0112345678'),
        ('فاطمة عبدالله', 'fatima@example.com', '0551234567'),
    ]
    
    for i, (name, email, phone) in enumerate(customers_data):
        # عميل Partners
        Customer.objects.get_or_create(
            name=name,
            defaults={'email': email, 'phone': phone}
        )
        
        # عميل CRM
        name_parts = name.split()
        first_name = name_parts[0]
        last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
        customer_code = f"CUS{(i+1):05d}"
        
        CRMCustomer.objects.get_or_create(
            customer_code=customer_code,
            defaults={
                'first_name': first_name,
                'last_name': last_name,
                'phone': phone,
                'email': email,
                'status': 'active'
            }
        )
    
    # 4. إنشاء موردين
    print("إنشاء الموردين...")
    suppliers_data = [
        ('شركة المواد الخام المحدودة', 'supplies@rawmat.com', '0114567890'),
        ('مصنع الإسفنج الطبي', 'info@medicalfoam.com', '0125678901'),
    ]
    
    for name, email, phone in suppliers_data:
        Supplier.objects.get_or_create(
            name=name,
            defaults={'email': email, 'phone': phone}
        )
    
    # 5. إنشاء أقسام ووظائف
    print("إنشاء الأقسام...")
    departments_data = [
        ('الإنتاج', 'PROD'),
        ('المبيعات', 'SALES'),
        ('المحاسبة', 'ACC'),
    ]
    
    for dept_name, dept_code in departments_data:
        dept, _ = Department.objects.get_or_create(
            code=dept_code,
            defaults={'name': dept_name, 'is_active': True}
        )
        
        # إنشاء وظيفة واحدة لكل قسم
        job_title = f'مدير {dept_name}'
        job_code = f"{dept_code}_MANAGER"
        
        JobPosition.objects.get_or_create(
            code=job_code,
            defaults={
                'title': job_title,
                'department': dept,
                'description': f'وصف وظيفي لـ {job_title}',
                'requirements': f'متطلبات وظيفة {job_title}',
                'min_salary': 5000,
                'max_salary': 15000,
                'is_active': True
            }
        )
    
    # 6. إنشاء مراحل الفرص
    print("إنشاء مراحل CRM...")
    stages_data = [
        ('عميل محتمل', 10, 1, False, False),
        ('مؤهل', 25, 2, False, False),
        ('عرض سعر', 50, 3, False, False),
        ('إغلاق ناجح', 100, 4, True, False),
        ('فاشل', 0, 5, False, True),
    ]
    
    for name, prob, order, is_won, is_lost in stages_data:
        OpportunityStage.objects.get_or_create(
            name=name,
            defaults={
                'probability': prob,
                'order': order,
                'is_won': is_won,
                'is_lost': is_lost
            }
        )
    
    # 7. إنشاء فواتير بسيطة
    print("إنشاء الفواتير...")
    customers = Customer.objects.all()[:2]
    products = Product.objects.all()[:3]
    
    for i in range(2):
        if customers and products:
            customer = customers[i % len(customers)]
            invoice_number = f"INV-{str(i+1).zfill(6)}"
            
            invoice, created = Invoice.objects.get_or_create(
                number=invoice_number,
                defaults={
                    'customer': customer,
                    'date': date.today() - timedelta(days=i+1)
                }
            )
            
            if created:
                # إضافة بند واحد للفاتورة
                product = products[0]
                InvoiceItem.objects.create(
                    invoice=invoice,
                    product=product,
                    location=main_location,
                    quantity=1,
                    price=float(product.price)
                )
    
    print("تم إنشاء البيانات التجريبية بنجاح!")
    print(f"   - المنتجات: {Product.objects.count()}")
    print(f"   - المواقع: {Location.objects.count()}")
    print(f"   - العملاء: {Customer.objects.count()}")
    print(f"   - الموردين: {Supplier.objects.count()}")
    print(f"   - الفواتير: {Invoice.objects.count()}")


if __name__ == '__main__':
    create_simple_data()