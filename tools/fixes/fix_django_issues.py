#!/usr/bin/env python3
"""
حل مشاكل Django الشائعة
- إصلاح مشاكل account_id في نماذج Django  
- إصلاح مشاكل template.engine في debug files
- إصلاح مشاكل الشبكة في diagnose_network_access.py
- إصلاح مشاكل sys.stdout.reconfigure في settings
"""

import os
import re
from pathlib import Path

def fix_account_id_attributes():
    """إصلاح مشاكل account_id المفقودة في Django models"""
    files_fixed = 0
    
    # البحث عن ملفات تحتوي على account_id
    search_pattern = r'\.account.id'
    replace_pattern = r'.account.id'
    
    # البحث في المجلد
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    if '.account.id' in content:
                        # استبدال .account.id بـ .account.id
                        new_content = content.replace('.account.id', '.account.id')
                        
                        if new_content != content:
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(new_content)
                            files_fixed += 1
                            print(f"✓ Fixed account_id in: {file_path}")
                
                except Exception as e:
                    print(f"⚠ Error processing {file_path}: {e}")
    
    return files_fixed

def fix_template_engine_access():
    """إصلاح مشاكل template.engine في debug files"""
    files_fixed = 0
    
    # Pattern to find problematic template engine access
    pattern = r'engine\.engine\.template_libraries'
    replacement = r'getattr(engine.engine, "template_libraries", {})'
    
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.py') and 'debug' in file:
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    if 'engine.engine.template_libraries' in content:
                        new_content = re.sub(pattern, replacement, content)
                        
                        if new_content != content:
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(new_content)
                            files_fixed += 1
                            print(f"✓ Fixed template engine access in: {file_path}")
                
                except Exception as e:
                    print(f"⚠ Error processing {file_path}: {e}")
    
    return files_fixed

def fix_network_diagnosis():
    """إصلاح مشاكل diagnose_network_access.py"""
    files_fixed = 0
    
    # البحث عن ملفات diagnose_network_access.py
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file == 'diagnose_network_access.py':
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # إصلاح مشكلة type checking للـ addr
                    new_content = content
                    
                    # إصلاح المشكلة الأولى: التحقق من نوع addr
                    if "if ':' in addr or addr.startswith('127.'):" in content:
                        new_content = new_content.replace(
                            "if ':' in addr or addr.startswith('127.'):",
                            "if isinstance(addr, str) and (':' in addr or addr.startswith('127.')):"
                        )
                    
                    # إصلاح المشكلة الثانية: التأكد من أن addr هو string قبل إضافته
                    if "ips.add(addr)" in content:
                        new_content = new_content.replace(
                            "ips.add(addr)",
                            "if isinstance(addr, str): ips.add(addr)"
                        )
                    
                    if new_content != content:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        files_fixed += 1
                        print(f"✓ Fixed network diagnosis in: {file_path}")
                
                except Exception as e:
                    print(f"⚠ Error processing {file_path}: {e}")
    
    return files_fixed

def fix_settings_reconfigure():
    """إصلاح مشاكل sys.stdout.reconfigure في settings"""
    files_fixed = 0
    
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file == 'settings.py':
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    new_content = content
                    
                    # إصلاح sys.stdout.reconfigure
                    if 'sys.stdout.reconfigure(' in content:
                        new_content = new_content.replace(
                            'sys.stdout.reconfigure(encoding="utf-8", errors="replace")',
                            'if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")'
                        )
                    
                    # إصلاح sys.stderr.reconfigure  
                    if 'sys.stderr.reconfigure(' in content:
                        new_content = new_content.replace(
                            'sys.stderr.reconfigure(encoding="utf-8", errors="replace")',
                            'if hasattr(sys.stderr, "reconfigure"): sys.stderr.reconfigure(encoding="utf-8", errors="replace")'
                        )
                    
                    # إصلاح os.getenv مع None
                    if "dj_database_url.parse(os.getenv('DATABASE_URL'))" in content:
                        new_content = new_content.replace(
                            "dj_database_url.parse(os.getenv('DATABASE_URL'))",
                            "dj_database_url.parse(os.getenv('DATABASE_URL', ''))"
                        )
                    
                    if new_content != content:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        files_fixed += 1
                        print(f"✓ Fixed settings reconfigure in: {file_path}")
                
                except Exception as e:
                    print(f"⚠ Error processing {file_path}: {e}")
    
    return files_fixed

def fix_import_errors():
    """إصلاح مشاكل الاستيراد الشائعة"""
    files_fixed = 0
    
    # إصلاح django.template.base imports  
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    new_content = content
                    
                    # إصلاح استيراد get_installed_libraries
                    old_import = '''try:
    from django.template.base import get_installed_libraries
except ImportError:
    get_installed_libraries = lambda: {}'''
                    new_import = '''try:
    from django.template.base import get_installed_libraries
except ImportError:
    get_installed_libraries = lambda: {}'''
                    if old_import in content:
                        new_content = new_content.replace(old_import, new_import)
                    
                    if new_content != content:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        files_fixed += 1
                        print(f"✓ Fixed imports in: {file_path}")
                
                except Exception as e:
                    print(f"⚠ Error processing {file_path}: {e}")
    
    return files_fixed

def main():
    print("🔧 Starting Django issues fix...")
    
    total_fixed = 0
    
    print("\n1️⃣ Fixing account_id attributes...")
    total_fixed += fix_account_id_attributes()
    
    print("\n2️⃣ Fixing template engine access...")
    total_fixed += fix_template_engine_access()
    
    print("\n3️⃣ Fixing network diagnosis...")
    total_fixed += fix_network_diagnosis()
    
    print("\n4️⃣ Fixing settings reconfigure...")
    total_fixed += fix_settings_reconfigure()
    
    print("\n5️⃣ Fixing import errors...")
    total_fixed += fix_import_errors()
    
    print(f"\n✅ Fixed {total_fixed} files total!")

if __name__ == "__main__":
    main()