from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from inventory.models import Product, Location, Stock
from partners.models import Customer, Supplier
from sales.models import Invoice, InvoiceItem
from purchases.models import PurchaseBill, PurchaseItem
from accounting.models import Account, AccountType
from hr.models import Employee, Department, JobPosition
from crm.models import Customer as CRMCustomer, Opportunity, OpportunityStage
from decimal import Decimal
from datetime import date, timedelta
import random


class Command(BaseCommand):
    help = 'إنشاء بيانات تجريبية للنظام'

    def handle(self, *args, **options):
        self.stdout.write("بدء إنشاء البيانات التجريبية...")
        try:
            self.create_sample_data()
            self.stdout.write(self.style.SUCCESS("تم إنشاء البيانات التجريبية بنجاح"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"خطأ في إنشاء البيانات: {e}"))

    def create_sample_data(self):
        # 1. مواقع المخازن
        self.stdout.write("إنشاء مواقع المخازن...")
        warehouse_main, _ = Location.objects.get_or_create(
            code='MAIN',
            defaults={'name': 'المخزن الرئيسي', 'type': 'other', 'is_default': True}
        )
        warehouse_raw, _ = Location.objects.get_or_create(
            code='RAW',
            defaults={'name': 'مخزن المواد الخام', 'type': 'raw'}
        )
        warehouse_finished, _ = Location.objects.get_or_create(
            code='FIN',
            defaults={'name': 'مخزن المنتجات المكتملة', 'type': 'finished'}
        )

        # 2. منتجات (موسّع - 25+ منتج)
        self.stdout.write("إنشاء منتجات...")
        products_data = [
            # مراتب
            ('MAT-001', 'مرتبة طبية مفردة 100×200', 1500.00, 900.00, 'unit', 10),
            ('MAT-002', 'مرتبة سوست زوجي 180×200', 2500.00, 1500.00, 'unit', 5),
            ('MAT-003', 'مرتبة إسفنج مفردة 120×200', 1200.00, 700.00, 'unit', 8),
            ('MAT-004', 'مرتبة ميموري فوم 160×200', 3500.00, 2100.00, 'unit', 4),
            ('MAT-005', 'مرتبة أطفال 70×140', 800.00, 450.00, 'unit', 15),
            ('MAT-006', 'مرتبة لاتكس طبيعي 180×200', 4500.00, 2800.00, 'unit', 3),
            # وسائد
            ('PIL-001', 'وسادة طبية فايبر', 150.00, 80.00, 'unit', 50),
            ('PIL-002', 'وسادة ميموري فوم', 250.00, 140.00, 'unit', 30),
            ('PIL-003', 'وسادة ريش طبيعي', 350.00, 200.00, 'unit', 20),
            ('PIL-004', 'وسادة أطفال', 100.00, 55.00, 'unit', 40),
            # خامات
            ('FOA-001', 'إسفنج عالي الكثافة D30', 25.00, 15.00, 'm', 100),
            ('FOA-002', 'إسفنج متوسط الكثافة D25', 20.00, 12.00, 'm', 150),
            ('FOA-003', 'إسفنج ميموري فوم', 45.00, 28.00, 'm', 80),
            ('FAB-001', 'قماش قطني أبيض', 45.00, 30.00, 'm', 200),
            ('FAB-002', 'قماش جاكار فاخر', 85.00, 55.00, 'm', 100),
            ('FAB-003', 'قماش مضاد للماء', 65.00, 40.00, 'm', 120),
            ('SPR-001', 'سوست معدنية بونيل', 8.50, 5.00, 'unit', 1000),
            ('SPR-002', 'سوست بوكت منفصلة', 15.00, 9.00, 'unit', 800),
            # إكسسوارات
            ('ACC-001', 'غطاء مرتبة قطني', 180.00, 100.00, 'unit', 30),
            ('ACC-002', 'غطاء مرتبة مضاد للماء', 250.00, 140.00, 'unit', 25),
            ('ACC-003', 'واقي مرتبة', 120.00, 70.00, 'unit', 35),
            ('ACC-004', 'توبر إسفنجي', 400.00, 230.00, 'unit', 20),
            # مواد تغليف
            ('PKG-001', 'كرتون تغليف كبير', 15.00, 8.00, 'unit', 200),
            ('PKG-002', 'بلاستيك شرنك', 5.00, 3.00, 'm', 500),
            ('PKG-003', 'شريط لاصق', 8.00, 4.50, 'unit', 100),
        ]
        for sku, name, price, cost, uom, min_stock in products_data:
            product, _ = Product.objects.get_or_create(
                sku=sku,
                defaults={
                    'name': name,
                    'price': Decimal(str(price)),
                    'cost': Decimal(str(cost)),
                    'purchase_uom': uom,
                    'usage_uom': uom,
                    'min_stock': min_stock
                }
            )
            for location in [warehouse_main, warehouse_raw, warehouse_finished]:
                Stock.objects.get_or_create(
                    product=product,
                    location=location,
                    defaults={'quantity': max(min_stock * 2, 10)}
                )

        # 3. عملاء وموردون (موسّع)
        self.stdout.write("إنشاء عملاء وموردين...")
        customers_data = [
            # العملاء الأفراد
            ('أحمد محمد', 'ahmed@example.com', '0501234567', 'الرياض'),
            ('فاطمة عبدالله', 'fatima@example.com', '0551234567', 'جدة'),
            ('محمود حسن', 'mahmoud@example.com', '0561234567', 'الدمام'),
            ('سارة علي', 'sara@example.com', '0571234567', 'مكة'),
            ('خالد عمر', 'khaled@example.com', '0581234567', 'المدينة'),
            # الشركات
            ('شركة النور للأثاث', 'info@alnoor.com', '0112345678', 'الرياض'),
            ('شركة الراحة للمفروشات', 'contact@raaha.com', '0123456789', 'جدة'),
            ('مؤسسة الأمل التجارية', 'amal@trade.com', '0134567890', 'الدمام'),
            ('شركة المنزل الحديث', 'modern@home.com', '0145678901', 'الخبر'),
            ('مفروشات الخليج', 'gulf@furnish.com', '0156789012', 'الرياض'),
        ]
        for i, (name, email, phone, *extra) in enumerate(customers_data):
            address = extra[0] if extra else ''
            Customer.objects.get_or_create(name=name, defaults={'email': email, 'phone': phone})
            parts = name.split()
            first_name = parts[0]
            last_name = ' '.join(parts[1:]) if len(parts) > 1 else ''
            CRMCustomer.objects.get_or_create(
                customer_code=f"CUS{(i+1):05d}",
                defaults={'first_name': first_name, 'last_name': last_name, 'phone': phone, 'email': email, 'status': 'active'}
            )
        
        # موردون موسّعون (5+ موردين)
        suppliers_data = [
            ('شركة المواد الخام المحدودة', 'supplies@rawmat.com', '0114567890', 'الرياض'),
            ('مصنع الإسفنج الطبي', 'info@medicalfoam.com', '0125678901', 'جدة'),
            ('شركة الأقمشة العربية', 'sales@arabfabrics.com', '0136789012', 'الدمام'),
            ('مصنع السوست الصناعية', 'springs@factory.com', '0147890123', 'الجبيل'),
            ('شركة الخشب الفاخر', 'wood@premium.com', '0158901234', 'الرياض'),
            ('مؤسسة المواد الكيماوية', 'chemicals@supply.com', '0169012345', 'ينبع'),
            ('شركة التغليف والتعبئة', 'packaging@co.com', '0170123456', 'جدة'),
        ]
        for name, email, phone, *extra in suppliers_data:
            Supplier.objects.get_or_create(name=name, defaults={'email': email, 'phone': phone})

        # 4. أقسام ووظائف (موسّع - 6 أقسام و12+ وظيفة)
        self.stdout.write("إنشاء أقسام ووظائف...")
        departments = [
            ('الإنتاج', 'PROD', 'قسم الإنتاج والتصنيع'),
            ('المبيعات', 'SALES', 'قسم المبيعات والتسويق'),
            ('الموارد البشرية', 'HR', 'قسم شؤون الموظفين'),
            ('المحاسبة', 'ACC', 'القسم المالي والمحاسبي'),
            ('الصيانة', 'MAINT', 'قسم الصيانة والدعم الفني'),
            ('المشتريات', 'PURCH', 'قسم المشتريات والتوريد'),
            ('الجودة', 'QA', 'قسم ضبط الجودة'),
            ('خدمة العملاء', 'CS', 'قسم خدمة العملاء'),
        ]
        positions_map = {
            'PROD': [
                ('مدير الإنتاج', 8000, 15000),
                ('مشرف الإنتاج', 5000, 8000),
                ('عامل إنتاج', 3000, 5000),
                ('فني تشغيل آلات', 4000, 7000),
            ],
            'SALES': [
                ('مدير المبيعات', 8000, 15000),
                ('مندوب مبيعات', 4000, 8000),
                ('مساعد مبيعات', 3000, 5000),
                ('مسؤول حسابات كبار العملاء', 6000, 10000),
            ],
            'HR': [
                ('مدير الموارد البشرية', 8000, 14000),
                ('أخصائي توظيف', 4000, 7000),
                ('مسؤول شؤون الموظفين', 3500, 6000),
            ],
            'ACC': [
                ('المدير المالي', 10000, 18000),
                ('محاسب عام', 4000, 7000),
                ('محاسب تكاليف', 5000, 9000),
                ('أمين صندوق', 3500, 5500),
            ],
            'MAINT': [
                ('مدير الصيانة', 6000, 10000),
                ('فني صيانة', 3500, 6000),
                ('كهربائي', 4000, 7000),
            ],
            'PURCH': [
                ('مدير المشتريات', 7000, 12000),
                ('مسؤول مشتريات', 4000, 7000),
                ('مسؤول مخازن', 3500, 6000),
            ],
            'QA': [
                ('مدير الجودة', 7000, 12000),
                ('مفتش جودة', 4000, 7000),
            ],
            'CS': [
                ('مدير خدمة العملاء', 6000, 10000),
                ('موظف خدمة عملاء', 3500, 6000),
            ],
        }
        for dept_name, dept_code, desc in departments:
            dept, _ = Department.objects.get_or_create(
                code=dept_code, 
                defaults={'name': dept_name, 'is_active': True}
            )
            positions = positions_map.get(dept_code, [])
            for pos_title, min_sal, max_sal in positions:
                safe_code = pos_title.replace(' ', '_')[:15]
                JobPosition.objects.get_or_create(
                    code=f"{dept_code}_{safe_code}".upper(),
                    defaults={
                        'title': pos_title,
                        'department': dept,
                        'description': f'وصف وظيفي لـ {pos_title} في قسم {dept_name}',
                        'requirements': f'متطلبات وظيفة {pos_title}',
                        'min_salary': min_sal,
                        'max_salary': max_sal,
                        'is_active': True
                    }
                )

        # 5. مراحل الفرص
        self.stdout.write("إنشاء مراحل CRM...")
        stages_data = [
            ('عميل محتمل', 10, 1, False, False),
            ('مؤهل', 25, 2, False, False),
            ('عرض سعر', 50, 3, False, False),
            ('تفاوض', 75, 4, False, False),
            ('إغلاق ناجح', 100, 5, True, False),
            ('فاشل', 0, 6, False, True),
        ]
        for name, prob, order, is_won, is_lost in stages_data:
            OpportunityStage.objects.get_or_create(
                name=name,
                defaults={'probability': prob, 'order': order, 'is_won': is_won, 'is_lost': is_lost}
            )

        # 6. فواتير وفرص
        self.stdout.write("إنشاء فواتير وفرص...")
        customers = list(Customer.objects.all()[:3])
        products = list(Product.objects.all()[:4])
        for i in range(3):
            if not customers:
                break
            customer = random.choice(customers)
            last_invoice = Invoice.objects.order_by('-id').first()
            if last_invoice:
                try:
                    last_number = int(last_invoice.number.split('-')[-1])
                    number = f"INV-{str(last_number + i + 1).zfill(6)}"
                except Exception:
                    number = f"INV-{str(Invoice.objects.count() + i + 1).zfill(6)}"
            else:
                number = f"INV-{str(i+1).zfill(6)}"
            invoice, created = Invoice.objects.get_or_create(
                number=number,
                defaults={'customer': customer, 'date': date.today() - timedelta(days=random.randint(1, 30))}
            )
            if created and products:
                for _ in range(random.randint(1, 2)):
                    product = random.choice(products)
                    InvoiceItem.objects.create(
                        invoice=invoice,
                        product=product,
                        location=warehouse_main,
                        quantity=random.randint(1, 3),
                        price=float(product.price) * random.uniform(0.9, 1.1)
                    )

        crm_customers = list(CRMCustomer.objects.all()[:3])
        stages = list(OpportunityStage.objects.all())
        users = list(User.objects.all()[:2])
        for _ in range(5):
            if not (crm_customers and stages):
                break
            customer = random.choice(crm_customers)
            stage = random.choice(stages[:4])
            user = random.choice(users) if users else None
            Opportunity.objects.get_or_create(
                name=f'فرصة {customer.first_name} - منتجات نوم',
                defaults={
                    'customer': customer,
                    'stage': stage,
                    'estimated_value': Decimal(str(random.randint(5000, 50000))),
                    'probability': stage.probability,
                    'expected_close_date': date.today() + timedelta(days=random.randint(7, 60)),
                    'assigned_to': user,
                    'description': f'فرصة بيع منتجات للعميل {customer.first_name}'
                }
            )

        # 7. بيانات الإنتاج (اختياري)
        self.stdout.write("إنشاء بيانات الإنتاج...")
        try:
            from production.models import ProductionWorkCenter, ProductionOrder
            production_dept = Department.objects.filter(name='الإنتاج').first()
            work_centers_data = [
                ('WC001', 'قسم التقطيع', 'cutting', 50.00),
                ('WC002', 'قسم الخياطة', 'sewing', 45.00),
                ('WC003', 'قسم التجميع', 'assembly', 40.00),
                ('WC004', 'قسم التعبئة', 'packaging', 35.00),
            ]
            for code, name, wc_type, hourly_rate in work_centers_data:
                ProductionWorkCenter.objects.get_or_create(
                    code=code,
                    defaults={
                        'name': name,
                        'work_center_type': wc_type,
                        'department': production_dept,
                        'hourly_rate': Decimal(str(hourly_rate)),
                        'is_active': True
                    }
                )
            products_production = Product.objects.filter(sku__startswith='MAT')[:3]
            for i, product in enumerate(products_production):
                order_number = f"PRO-{date.today().strftime('%Y%m%d')}-{i+1:03d}"
                ProductionOrder.objects.get_or_create(
                    number=order_number,
                    defaults={
                        'product': product,
                        'planned_quantity': random.randint(10, 50),
                        'priority': random.choice(['normal', 'high', 'urgent']),
                        'status': random.choice(['confirmed', 'in_progress', 'completed']),
                        'planned_start_date': date.today() + timedelta(days=random.randint(1, 7)),
                        'planned_end_date': date.today() + timedelta(days=random.randint(8, 30)),
                        'notes': f'أمر إنتاج {product.name}'
                    }
                )
        except Exception as e:
            self.stdout.write(f"تحذير: تخطي بيانات الإنتاج: {e}")

        # ملخص
        self.stdout.write("ملخص البيانات المُنشأة:")
        self.stdout.write(f"   - المنتجات: {Product.objects.count()}")
        self.stdout.write(f"   - المواقع: {Location.objects.count()}")
        self.stdout.write(f"   - العملاء: {Customer.objects.count()}")
        self.stdout.write(f"   - الموردين: {Supplier.objects.count()}")
        self.stdout.write(f"   - فواتير المبيعات: {Invoice.objects.count()}")
        self.stdout.write(f"   - الفرص التجارية: {Opportunity.objects.count()}")
        try:
            from production.models import ProductionOrder, ProductionWorkCenter
            self.stdout.write(f"   - أوامر الإنتاج: {ProductionOrder.objects.count()}")
            self.stdout.write(f"   - مراكز العمل: {ProductionWorkCenter.objects.count()}")
        except Exception:
            pass