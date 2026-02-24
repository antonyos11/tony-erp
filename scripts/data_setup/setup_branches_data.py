#!/usr/bin/env python3
"""
سكريبت لإنشاء بيانات تجريبية للفروع والمعارض
"""
import os
import sys
import django

# إعداد Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from branches.models import Branch
from django.contrib.auth import get_user_model

User = get_user_model()

def create_sample_branches():
    """إنشاء فروع تجريبية"""
    
    # الحصول على أول مستخدم admin
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        admin_user = User.objects.filter(is_staff=True).first()
    
    if not admin_user:
        print("⚠️  لا يوجد مستخدم admin في النظام")
        return
    
    branches_data = [
        {
            'code': 'BR001',
            'name': 'الفرع الرئيسي - الرياض',
            'branch_type': 'main',
            'status': 'active',
            'city': 'الرياض',
            'address': 'شارع الملك فهد، الرياض',
            'phone': '0112345678',
            'email': 'riyadh@tonyerp.com',
            'is_main': True,
            'is_active': True,
        },
        {
            'code': 'BR002',
            'name': 'فرع جدة',
            'branch_type': 'branch',
            'status': 'active',
            'city': 'جدة',
            'address': 'شارع التحلية، جدة',
            'phone': '0122345678',
            'email': 'jeddah@tonyerp.com',
            'is_active': True,
        },
        {
            'code': 'SH001',
            'name': 'معرض الخبر',
            'branch_type': 'showroom',
            'status': 'active',
            'city': 'الخبر',
            'address': 'الكورنيش، الخبر',
            'phone': '0132345678',
            'email': 'khobar@tonyerp.com',
            'is_active': True,
        },
        {
            'code': 'WH001',
            'name': 'مستودع الدمام',
            'branch_type': 'warehouse',
            'status': 'active',
            'city': 'الدمام',
            'address': 'المنطقة الصناعية، الدمام',
            'phone': '0132345679',
            'email': 'dammam@tonyerp.com',
            'is_active': True,
        },
        {
            'code': 'SH002',
            'name': 'معرض مكة',
            'branch_type': 'showroom',
            'status': 'active',
            'city': 'مكة المكرمة',
            'address': 'شارع العزيزية، مكة',
            'phone': '0122345679',
            'email': 'makkah@tonyerp.com',
            'is_active': True,
        },
    ]
    
    created_count = 0
    updated_count = 0
    
    for data in branches_data:
        try:
            branch, created = Branch.objects.update_or_create(
                code=data['code'],
                defaults={
                    **data,
                    'created_by': admin_user,
                }
            )
            
            if created:
                created_count += 1
                print(f"✓ تم إنشاء الفرع: {branch.name} ({branch.code})")
            else:
                updated_count += 1
                print(f"✓ تم تحديث الفرع: {branch.name} ({branch.code})")
                
        except Exception as e:
            print(f"✗ خطأ في إنشاء/تحديث الفرع {data['code']}: {e}")
    
    print("\n" + "="*60)
    print(f"📊 الإحصائيات:")
    print(f"   - تم إنشاء: {created_count} فرع")
    print(f"   - تم تحديث: {updated_count} فرع")
    print(f"   - إجمالي الفروع في النظام: {Branch.objects.count()}")
    print("="*60)

if __name__ == '__main__':
    print("\n🚀 بدء إنشاء البيانات التجريبية للفروع...\n")
    create_sample_branches()
    print("\n✅ تم الانتهاء بنجاح!\n")
