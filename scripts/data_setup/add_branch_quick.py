#!/usr/bin/env python3
"""
إضافة فرع بسرعة - طريقة مبسطة
الاستخدام: python3 add_branch_quick.py
"""
import os, sys, django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from branches.models import Branch
from django.contrib.auth import get_user_model

User = get_user_model()

# معلومات الفرع الجديد - عدلها كما تريد
BRANCH_DATA = {
    'code': 'BR003',  # كود الفرع
    'name': 'فرع المدينة المنورة',  # اسم الفرع
    'branch_type': 'branch',  # نوع: main, branch, showroom, warehouse, factory
    'status': 'active',  # الحالة: active, inactive, under_construction
    'city': 'المدينة المنورة',
    'address': 'طريق الملك عبدالعزيز',
    'phone': '0142345678',
    'email': 'madinah@tonyerp.com',
    'is_active': True,
}

def add_branch():
    admin = User.objects.filter(is_superuser=True).first()
    if not admin:
        admin = User.objects.filter(is_staff=True).first()
    
    branch, created = Branch.objects.update_or_create(
        code=BRANCH_DATA['code'],
        defaults={**BRANCH_DATA, 'created_by': admin}
    )
    
    if created:
        print(f"✅ تم إنشاء الفرع: {branch.name} ({branch.code})")
    else:
        print(f"ℹ️  الفرع موجود مسبقاً وتم تحديثه: {branch.name}")
    
    print(f"\n🔗 رابط الفرع: /branches/{branch.pk}/")
    return branch

if __name__ == '__main__':
    print("\n" + "="*60)
    print("⚡ إضافة فرع سريع")
    print("="*60)
    add_branch()
    print("="*60 + "\n")
