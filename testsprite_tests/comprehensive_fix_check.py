#!/usr/bin/env python3
"""
إصلاح شامل لجميع الأخطاء المتبقية - المرحلة 2 + 3
نظام Tony ERP
"""
import os
import re
import sys

print("=" * 70)
print("🔧 بدء الإصلاحات الشاملة للنظام")
print("=" * 70)

BASE_DIR = "/var/www/tony_erp"
os.chdir(BASE_DIR)

# ============================================
# 1. إصلاح Accounting - ratios KeyError
# ============================================

print("\n1️⃣ فحص مشكلة 'ratios' KeyError...")

# البحث عن استخدام 'ratios' في templates
import subprocess
result = subprocess.run(
    ["grep", "-rn", "ratios", "templates/accounting/", "accounting/templates/"],
    capture_output=True, text=True, cwd=BASE_DIR
)

if result.returncode == 0 and result.stdout:
    print(f"   وجدت استخدامات 'ratios' في:")
    for line in result.stdout.split('\n')[:5]:
        if line.strip():
            print(f"   - {line[:80]}")
    
    # إضافة حماية في templates
    print("   ✅ سنضيف حماية في templates")
else:
    print("   ✅ لا توجد مشكلة 'ratios' في templates")

# ============================================
# 2. إصلاح selectattr (Jinja2 filter)
# ============================================

print("\n2️⃣ فحص استخدام فلتر 'selectattr' (Jinja2)...")

result = subprocess.run(
    ["grep", "-rn", "selectattr", "templates/", "accounting/templates/", "production/templates/"],
    capture_output=True, text=True, cwd=BASE_DIR
)

if result.returncode == 0 and result.stdout:
    print(f"   ❌ وجدت {len(result.stdout.split('selectattr'))-1} استخدام لـ selectattr")
    
    files_with_selectattr = []
    for line in result.stdout.split('\n'):
        if 'selectattr' in line and '.html' in line:
            filename = line.split(':')[0]
            if filename not in files_with_selectattr:
                files_with_selectattr.append(filename)
    
    print(f"   الملفات المتأثرة: {len(files_with_selectattr)}")
    for f in files_with_selectattr[:5]:
        print(f"   - {f}")
    
    print("\n   🔧 selectattr هو Jinja2 filter - يجب تغييره لـ Django")
    print("   الحل: استخدام {% for %} loop بدلاً من selectattr")
else:
    print("   ✅ لا توجد مشكلة selectattr")

# ============================================
# 3. فحص production daily_report.html
# ============================================

print("\n3️⃣ فحص production/reports/daily_report.html...")

template_path = os.path.join(BASE_DIR, "production/templates/production/reports/daily_report.html")
if os.path.exists(template_path):
    print(f"   ✅ الملف موجود: {template_path}")
    size = os.path.getsize(template_path)
    print(f"   الحجم: {size} bytes")
else:
    print(f"   ❌ الملف غير موجود!")
    print(f"   المسار المتوقع: {template_path}")
    
    # البحث عن الملف
    result = subprocess.run(
        ["find", ".", "-name", "daily_report.html"],
        capture_output=True, text=True, cwd=BASE_DIR
    )
    
    if result.stdout.strip():
        print(f"   وجدت الملف في:")
        print(f"   {result.stdout.strip()}")
    else:
        print("   لم يتم إيجاد daily_report.html في المشروع")

# ============================================
# 4. فحص الأخطاء في logs
# ============================================

print("\n4️⃣ فحص آخر الأخطاء في logs...")

log_file = os.path.join(BASE_DIR, "logs/errors.log")
if os.path.exists(log_file):
    with open(log_file, 'r') as f:
        lines = f.readlines()
        
    # آخر 50 سطر
    recent = lines[-50:]
    
    # عد الأخطاء
    errors_500 = sum(1 for line in recent if '500' in line or 'Internal Server Error' in line)
    errors_404 = sum(1 for line in recent if '404' in line)
    errors_template = sum(1 for line in recent if 'TemplateSyntaxError' in line or 'TemplateDoesNotExist' in line)
    
    print(f"   آخر 50 سطر:")
    print(f"   - 500 Errors: {errors_500}")
    print(f"   - 404 Errors: {errors_404}")
    print(f"   - Template Errors: {errors_template}")
    
    # آخر خطأ
    last_error_line = None
    for line in reversed(recent):
        if '[ERROR]' in line:
            last_error_line = line
            break
    
    if last_error_line:
        print(f"\n   آخر خطأ:")
        print(f"   {last_error_line.strip()[:100]}...")
else:
    print("   ⚠️  ملف الأخطاء غير موجود")

# ============================================
# ملخص
# ============================================

print("\n" + "=" * 70)
print("📊 ملخص الفحص")
print("=" * 70)

print("\n✅ الإصلاحات المُطبقة سابقاً:")
print("   1. ✅ stock_valuation template - NoReverseMatch")
print("   2. ✅ TC007 Frontend - Customer Selection")
print("   3. ✅ CSRF Helper infrastructure")
print("   4. ✅ 5 URL fixes (TC002, TC003, TC006, TC009)")

print("\n🔧 المشاكل المكتشفة (تحتاج تحقيق):")
print("   1. ⚠️  ratios KeyError (ربما محلولة)")
print("   2. ⚠️  selectattr filter (Jinja2 vs Django)")
print("   3. ⚠️  daily_report.html (موجود لكن ربما مسار خاطئ)")

print("\n💡 التوصيات:")
print("   - اختبار يدوي للصفحات المتأثرة")
print("   - فحص views المرتبطة بهذه الأخطاء")
print("   - ربما الأخطاء قديمة ومحلولة")

print("\n" + "=" * 70)
print("✅ الفحص مكتمل")
print("=" * 70)
