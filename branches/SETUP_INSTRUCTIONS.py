# إعدادات إضافة وحدة الفروع والمعارض الموحدة
# =============================================
# 
# لدمج الفروع والمعارض في نظام واحد، اتبع الخطوات التالية:

# ============================================
# 1. إضافة التطبيق في settings.py
# ============================================

INSTALLED_APPS = [
    # ... التطبيقات الأخرى
    'branches',
]

# ============================================
# 2. إضافة Context Processors في settings.py
# ============================================

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                # ... المعالجات الأخرى
                'branches.context_processors.current_location',
                'branches.context_processors.location_permissions',
            ],
        },
    },
]

# ============================================
# 3. إضافة URLs في urls.py الرئيسي
# ============================================

from django.urls import path, include

urlpatterns = [
    # ... المسارات الأخرى
    path('branches/', include('branches.urls')),
]

# ============================================
# 4. تحديث الـ Navbar في base.html
# ============================================
"""
<!-- استبدل dropdown المعرض الحالي بـ: -->
{% include 'branches/partials/_location_selector.html' with 
    branches=all_branches 
    showrooms=all_showrooms 
    warehouses=all_warehouses
    current_location=current_location 
    current_id=current_location.id %}
"""

# ============================================
# 5. تحديث القائمة الجانبية (Sidebar)
# ============================================
"""
<!-- استبدل قسم "إدارة الفروع والمعارض" بـ: -->
<li class="sidebar-group" data-module="branches_mgmt">
    <button class="sidebar-collapse-btn sidebar-flyout-trigger" type="button">
        <i class="bi-building me-2"></i>
        <span>إدارة الفروع والمعارض</span>
        <i class="bi bi-chevron-down ms-auto toggle-icon"></i>
    </button>
    <ul class="collapse sidebar-submenu">
        <li class="submenu-header">الفروع والمعارض</li>
        <li><a href="{% url 'branches:dashboard' %}">لوحة التحكم</a></li>
        <li><a href="{% url 'branches:list' %}">قائمة المواقع</a></li>
        <li><a href="{% url 'branches:list' %}?type=branch">الفروع</a></li>
        <li><a href="{% url 'branches:list' %}?type=showroom">المعارض</a></li>
        <li><a href="{% url 'branches:list' %}?type=warehouse">المخازن</a></li>
        <li><a href="{% url 'branches:create' %}">إضافة موقع جديد</a></li>
        <li class="submenu-divider"></li>
        <li class="submenu-header">التحويلات</li>
        <li><a href="{% url 'branches:transfers' %}">تحويلات المواقع</a></li>
        <li><a href="{% url 'branches:transfers_create' %}">تحويل جديد</a></li>
    </ul>
</li>
"""

# ============================================
# 6. تشغيل Migrations
# ============================================
"""
python manage.py makemigrations branches
python manage.py migrate branches
"""

# ============================================
# 7. نقل البيانات من الجداول القديمة (اختياري)
# ============================================
"""
# إنشاء migration لنقل البيانات
# branches/migrations/0002_migrate_old_data.py

from django.db import migrations

def migrate_showrooms_to_branches(apps, schema_editor):
    '''نقل بيانات المعارض القديمة'''
    OldShowroom = apps.get_model('old_app', 'Showroom')  # غيّر حسب التطبيق
    Branch = apps.get_model('branches', 'Branch')
    
    for sr in OldShowroom.objects.all():
        Branch.objects.create(
            name=sr.name,
            code=f'SR-{sr.id:04d}',
            branch_type='showroom',
            address=getattr(sr, 'address', ''),
            city=getattr(sr, 'city', ''),
            phone=getattr(sr, 'phone', ''),
            is_active=getattr(sr, 'is_active', True),
        )

def migrate_branches_to_unified(apps, schema_editor):
    '''نقل بيانات الفروع القديمة'''
    OldBranch = apps.get_model('dashboard', 'Branch')  # غيّر حسب التطبيق
    Branch = apps.get_model('branches', 'Branch')
    
    for br in OldBranch.objects.all():
        Branch.objects.create(
            name=br.name,
            code=f'BR-{br.id:04d}',
            branch_type='branch',
            address=getattr(br, 'address', ''),
            city=getattr(br, 'city', ''),
            phone=getattr(br, 'phone', ''),
            is_active=getattr(br, 'is_active', True),
            is_main=getattr(br, 'is_main', False),
        )

class Migration(migrations.Migration):
    dependencies = [
        ('branches', '0001_initial'),
    ]
    
    operations = [
        migrations.RunPython(migrate_branches_to_unified, migrations.RunPython.noop),
        migrations.RunPython(migrate_showrooms_to_branches, migrations.RunPython.noop),
    ]
"""
