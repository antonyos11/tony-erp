"""
أوامر سريعة لإضافة فروع من Django Shell
نسخ والصق في: python3 manage.py shell
"""

# طريقة 1: إنشاء فرع بسيط
from branches.models import Branch
from django.contrib.auth import get_user_model
User = get_user_model()
admin = User.objects.filter(is_superuser=True).first()

Branch.objects.create(
    code='BR004',
    name='فرع أبها',
    branch_type='branch',
    status='active',
    city='أبها',
    phone='0172345678',
    created_by=admin
)

# طريقة 2: إنشاء عدة فروع دفعة واحدة
branches = [
    {'code': 'BR005', 'name': 'فرع تبوك', 'city': 'تبوك'},
    {'code': 'BR006', 'name': 'فرع حائل', 'city': 'حائل'},
    {'code': 'SH003', 'name': 'معرض الطائف', 'city': 'الطائف', 'branch_type': 'showroom'},
]

for b in branches:
    Branch.objects.create(
        code=b['code'],
        name=b['name'],
        city=b.get('city', ''),
        branch_type=b.get('branch_type', 'branch'),
        status='active',
        created_by=admin
    )
    print(f"✓ {b['name']}")
