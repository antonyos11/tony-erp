"""
إنشاء بيانات تجريبية للوحدات الجديدة
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
import random

User = get_user_model()
admin_user = User.objects.filter(is_superuser=True).first()

print("=" * 50)
print("إنشاء بيانات تجريبية للوحدات الجديدة")
print("=" * 50)

# 1. إنشاء فروع
print("\n1. إنشاء الفروع...")
from branches.models import Branch, BranchStaff

branches_data = [
    {'name': 'الفرع الرئيسي', 'code': 'HQ', 'city': 'الرياض', 'is_main': True},
    {'name': 'فرع جدة', 'code': 'JED', 'city': 'جدة', 'is_main': False},
    {'name': 'فرع الدمام', 'code': 'DMM', 'city': 'الدمام', 'is_main': False},
    {'name': 'فرع مكة', 'code': 'MKH', 'city': 'مكة المكرمة', 'is_main': False},
    {'name': 'فرع المدينة', 'code': 'MED', 'city': 'المدينة المنورة', 'is_main': False},
]

for data in branches_data:
    branch, created = Branch.objects.get_or_create(
        code=data['code'],
        defaults={
            'name': data['name'],
            'city': data['city'],
            'is_main': data['is_main'],
            'is_active': True,
            'address': f"شارع الملك فهد، {data['city']}",
            'phone': f"+966 5{random.randint(10000000, 99999999)}",
            'created_by': admin_user,
        }
    )
    if created:
        print(f"   ✅ {branch.name}")

# 2. إنشاء سنوات مالية وميزانيات
print("\n2. إنشاء السنوات المالية والميزانيات...")
from budgeting.models import FiscalYear, Budget, BudgetLine

fy, created = FiscalYear.objects.get_or_create(
    code='FY2026',
    defaults={
        'name': 'السنة المالية 2026',
        'start_date': timezone.now().replace(month=1, day=1).date(),
        'end_date': timezone.now().replace(month=12, day=31).date(),
        'status': 'active',
        'is_current': True,
        'created_by': admin_user,
    }
)
if created:
    print(f"   ✅ السنة المالية 2026")

budgets_data = [
    {'name': 'ميزانية المبيعات', 'code': 'BUD-SALES', 'type': 'revenue', 'amount': 5000000},
    {'name': 'ميزانية المشتريات', 'code': 'BUD-PURCH', 'type': 'expense', 'amount': 3000000},
    {'name': 'ميزانية الرواتب', 'code': 'BUD-SAL', 'type': 'expense', 'amount': 2000000},
    {'name': 'ميزانية التسويق', 'code': 'BUD-MKT', 'type': 'expense', 'amount': 500000},
]

for data in budgets_data:
    budget, created = Budget.objects.get_or_create(
        code=data['code'],
        defaults={
            'name': data['name'],
            'fiscal_year': fy,
            'budget_type': data['type'],
            'total_amount': Decimal(str(data['amount'])),
            'status': 'approved',
            'start_date': fy.start_date,
            'end_date': fy.end_date,
            'created_by': admin_user,
        }
    )
    if created:
        print(f"   ✅ {budget.name}")

# 3. إنشاء معايير وفحوصات الجودة
print("\n3. إنشاء معايير الجودة...")
from quality_control.models import QualityStandard, InspectionType, QualityInspection

standards_data = [
    {'name': 'فحص المظهر الخارجي', 'code': 'QS-APP', 'category': 'مظهر'},
    {'name': 'فحص الأبعاد', 'code': 'QS-DIM', 'category': 'أبعاد', 'min': 0, 'max': 100},
    {'name': 'فحص الوزن', 'code': 'QS-WGT', 'category': 'وزن', 'min': 0, 'max': 1000},
    {'name': 'فحص اللون', 'code': 'QS-CLR', 'category': 'مظهر'},
    {'name': 'فحص التغليف', 'code': 'QS-PKG', 'category': 'تغليف'},
]

for data in standards_data:
    std, created = QualityStandard.objects.get_or_create(
        code=data['code'],
        defaults={
            'name': data['name'],
            'category': data['category'],
            'min_value': data.get('min'),
            'max_value': data.get('max'),
            'is_active': True,
            'created_by': admin_user,
        }
    )
    if created:
        print(f"   ✅ {std.name}")

inspection_types = [
    {'name': 'فحص استلام المواد', 'code': 'IT-RCV'},
    {'name': 'فحص الإنتاج', 'code': 'IT-PRD'},
    {'name': 'فحص ما قبل الشحن', 'code': 'IT-SHP'},
]

for data in inspection_types:
    it, created = InspectionType.objects.get_or_create(
        code=data['code'],
        defaults={'name': data['name'], 'is_active': True}
    )
    if created:
        it.standards.set(QualityStandard.objects.all()[:3])
        print(f"   ✅ {it.name}")

# 4. إنشاء برامج الولاء
print("\n4. إنشاء برامج الولاء...")
from loyalty.models import LoyaltyProgram, LoyaltyTier, LoyaltyReward

program, created = LoyaltyProgram.objects.get_or_create(
    code='GOLD-PROGRAM',
    defaults={
        'name': 'برنامج الولاء الذهبي',
        'description': 'اكسب نقاط مع كل عملية شراء',
        'points_per_unit': Decimal('1'),
        'redemption_rate': Decimal('0.01'),
        'min_points_redeem': 100,
        'is_active': True,
    }
)
if created:
    print(f"   ✅ {program.name}")
    
    # إنشاء المستويات
    tiers_data = [
        {'name': 'برونزي', 'min_points': 0, 'multiplier': 1, 'discount': 0, 'color': '#CD7F32'},
        {'name': 'فضي', 'min_points': 1000, 'multiplier': 1.25, 'discount': 5, 'color': '#C0C0C0'},
        {'name': 'ذهبي', 'min_points': 5000, 'multiplier': 1.5, 'discount': 10, 'color': '#FFD700'},
        {'name': 'بلاتيني', 'min_points': 10000, 'multiplier': 2, 'discount': 15, 'color': '#E5E4E2'},
    ]
    
    for tier_data in tiers_data:
        LoyaltyTier.objects.create(
            program=program,
            name=tier_data['name'],
            min_points=tier_data['min_points'],
            points_multiplier=Decimal(str(tier_data['multiplier'])),
            discount_percentage=Decimal(str(tier_data['discount'])),
            color=tier_data['color'],
        )
        print(f"      ✅ مستوى {tier_data['name']}")

# إنشاء مكافآت
rewards_data = [
    {'name': 'خصم 50 ج.م', 'points': 500, 'type': 'discount', 'value': 50},
    {'name': 'خصم 100 ج.م', 'points': 900, 'type': 'discount', 'value': 100},
    {'name': 'شحن مجاني', 'points': 300, 'type': 'voucher', 'value': 30},
    {'name': 'هدية مجانية', 'points': 1000, 'type': 'product', 'value': 0},
]

for data in rewards_data:
    reward, created = LoyaltyReward.objects.get_or_create(
        name=data['name'],
        program=program,
        defaults={
            'points_cost': data['points'],
            'reward_type': data['type'],
            'reward_value': Decimal(str(data['value'])),
            'is_active': True,
        }
    )
    if created:
        print(f"   ✅ مكافأة: {reward.name}")

# 5. إنشاء فئات وتذاكر الدعم
print("\n5. إنشاء فئات الدعم...")
from helpdesk.models import TicketCategory, Ticket, KnowledgeBase

categories_data = [
    {'name': 'دعم فني', 'code': 'TECH', 'sla': 4},
    {'name': 'استفسارات عامة', 'code': 'GEN', 'sla': 24},
    {'name': 'شكاوى', 'code': 'COMP', 'sla': 2},
    {'name': 'اقتراحات', 'code': 'SUGG', 'sla': 48},
    {'name': 'طلبات جديدة', 'code': 'REQ', 'sla': 8},
]

for data in categories_data:
    cat, created = TicketCategory.objects.get_or_create(
        code=data['code'],
        defaults={
            'name': data['name'],
            'sla_hours': data['sla'],
            'is_active': True,
        }
    )
    if created:
        print(f"   ✅ {cat.name}")

# إنشاء تذاكر تجريبية
tickets_data = [
    {'subject': 'مشكلة في تسجيل الدخول', 'priority': 'high', 'status': 'open'},
    {'subject': 'استفسار عن الأسعار', 'priority': 'medium', 'status': 'pending'},
    {'subject': 'طلب ميزة جديدة', 'priority': 'low', 'status': 'new'},
    {'subject': 'مشكلة في الطباعة', 'priority': 'medium', 'status': 'resolved'},
]

tech_cat = TicketCategory.objects.filter(code='TECH').first()
for i, data in enumerate(tickets_data, 1):
    ticket, created = Ticket.objects.get_or_create(
        ticket_number=f'TKT-{i:06d}',
        defaults={
            'subject': data['subject'],
            'description': f"وصف تفصيلي للتذكرة: {data['subject']}",
            'category': tech_cat,
            'priority': data['priority'],
            'status': data['status'],
            'created_by': admin_user,
        }
    )
    if created:
        print(f"   ✅ تذكرة: {ticket.ticket_number}")

# إنشاء مقالات قاعدة المعرفة
kb_articles = [
    {'title': 'كيفية تسجيل الدخول', 'slug': 'how-to-login'},
    {'title': 'دليل المستخدم السريع', 'slug': 'quick-start-guide'},
    {'title': 'الأسئلة الشائعة', 'slug': 'faq'},
]

for data in kb_articles:
    kb, created = KnowledgeBase.objects.get_or_create(
        slug=data['slug'],
        defaults={
            'title': data['title'],
            'content': f"# {data['title']}\n\nمحتوى المقال هنا...",
            'is_published': True,
            'created_by': admin_user,
        }
    )
    if created:
        print(f"   ✅ مقال: {kb.title}")

# 6. إنشاء بنوك وكشوف حساب
print("\n6. إنشاء بيانات مطابقة البنوك...")
from bank_reconciliation.models import BankStatement, Reconciliation

try:
    from accounting.models import Bank
    bank = Bank.objects.first()
    if bank:
        statement, created = BankStatement.objects.get_or_create(
            bank_account=bank,
            statement_date=timezone.now().date(),
            defaults={
                'start_date': timezone.now().date() - timedelta(days=30),
                'end_date': timezone.now().date(),
                'opening_balance': Decimal('100000'),
                'closing_balance': Decimal('125000'),
                'status': 'pending',
                'created_by': admin_user,
            }
        )
        if created:
            print(f"   ✅ كشف حساب بنكي")
except Exception as e:
    print(f"   ⚠️ لم يتم إنشاء بيانات البنك: {e}")

print("\n" + "=" * 50)
print("✅ تم إنشاء البيانات التجريبية بنجاح!")
print("=" * 50)
