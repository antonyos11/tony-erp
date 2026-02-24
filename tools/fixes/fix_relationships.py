#!/usr/bin/env python3
"""
حل مشاكل العلاقات المفقودة في Django models
- إضافة type hints للعلاقات المعكوسة
- إصلاح مشاكل journal_entries, items, payments relationships
- إضافة TYPE_CHECKING imports
"""

import os
import re
from pathlib import Path

def add_type_checking_imports():
    """إضافة TYPE_CHECKING imports للنماذج التي تحتاجها"""
    files_fixed = 0
    
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('models.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # التحقق من وجود TYPE_CHECKING
                    if 'TYPE_CHECKING' not in content and 'from typing import' in content:
                        new_content = content
                        
                        # إضافة TYPE_CHECKING import
                        if 'from typing import' in content:
                            new_content = re.sub(
                                r'(from typing import [^\\n]+)',
                                r'\1, TYPE_CHECKING',
                                content
                            )
                        else:
                            # إضافة import جديد
                            new_content = 'from typing import TYPE_CHECKING\n' + content
                        
                        # إضافة if TYPE_CHECKING block قبل النماذج
                        if 'if TYPE_CHECKING:' not in new_content:
                            # البحث عن أول model class
                            model_match = re.search(r'^class \w+\(models\.Model\):', new_content, re.MULTILINE)
                            if model_match:
                                insert_pos = model_match.start()
                                type_checking_block = '''
if TYPE_CHECKING:
    from django.db.models import QuerySet
    from django.db.models.manager import RelatedManager

'''
                                new_content = new_content[:insert_pos] + type_checking_block + new_content[insert_pos:]
                        
                        if new_content != content:
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(new_content)
                            files_fixed += 1
                            print(f"✓ Added TYPE_CHECKING imports to: {file_path}")
                
                except Exception as e:
                    print(f"⚠ Error processing {file_path}: {e}")
    
    return files_fixed

def add_relationship_type_hints():
    """إضافة type hints للعلاقات المعكوسة"""
    files_fixed = 0
    
    # قائمة العلاقات الشائعة التي نحتاج لإضافة type hints لها
    relationships = {
        'journal_entries': 'RelatedManager[JournalEntryItem]',
        'items': 'RelatedManager[JournalEntryItem]',
        'payments': 'RelatedManager[LoanPayment]',
        'stocks': 'RelatedManager[Stock]',
        'invoices': 'RelatedManager[Invoice]',
        'orders': 'RelatedManager[Order]',
        'transfers': 'RelatedManager[Transfer]',
    }
    
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('models.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    new_content = content
                    
                    # البحث عن model classes وإضافة type hints
                    for model_match in re.finditer(r'^class (\w+)\(models\.Model\):(.*?)(?=^class |\Z)', content, re.MULTILINE | re.DOTALL):
                        model_name = model_match.group(1)
                        model_content = model_match.group(2)
                        
                        # إضافة type hints للعلاقات المعكوسة
                        if 'TYPE_CHECKING' in content:
                            for rel_name, rel_type in relationships.items():
                                if f'related_name=\'{rel_name}\'' in model_content or f'related_name="{rel_name}"' in model_content:
                                    # البحث عن نهاية الكلاس وإضافة type hint
                                    type_hint = f'    if TYPE_CHECKING:\n        {rel_name}: {rel_type}\n'
                                    
                                    # إضافة type hint في نهاية الكلاس إذا لم يكن موجوداً
                                    if f'{rel_name}: {rel_type}' not in model_content:
                                        class_end = model_match.end()
                                        new_content = new_content[:class_end-1] + '\n' + type_hint + new_content[class_end-1:]
                    
                    if new_content != content:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        files_fixed += 1
                        print(f"✓ Added relationship type hints to: {file_path}")
                
                except Exception as e:
                    print(f"⚠ Error processing {file_path}: {e}")
    
    return files_fixed

def fix_specific_relationship_issues():
    """إصلاح مشاكل محددة في العلاقات"""
    files_fixed = 0
    
    # إصلاح مشاكل account.parent assignment
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    new_content = content
                    
                    # إصلاح if parent_obj: account.parent = parent_obj
                    if 'if parent_obj: account.parent = parent_obj' in content:
                        new_content = new_content.replace(
                            'if parent_obj: account.parent = parent_obj',
                            'if parent_obj: if parent_obj: account.parent = parent_obj'
                        )
                    
                    # إصلاح database settings access
                    if "DATABASES['default'].get('ENGINE', '').split('.')[-1]" in content:
                        new_content = new_content.replace(
                            "DATABASES['default'].get('ENGINE', '').split('.')[-1]",
                            "DATABASES['default'].get('ENGINE', '').split('.')[-1]"
                        )
                    
                    if new_content != content:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        files_fixed += 1
                        print(f"✓ Fixed specific relationship issues in: {file_path}")
                
                except Exception as e:
                    print(f"⚠ Error processing {file_path}: {e}")
    
    return files_fixed

def add_import_fallbacks():
    """إضافة fallbacks للاستيرادات المفقودة"""
    files_fixed = 0
    
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.py') and 'debug' in file:
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    new_content = content
                    
                    # إضافة fallback لـ get_installed_libraries
                    if 'from django.template.base import get_installed_libraries' in content and 'except ImportError:' not in content:
                        new_content = new_content.replace(
                            'from django.template.base import get_installed_libraries',
                            '''try:
    from django.template.base import get_installed_libraries
except ImportError:
    def get_installed_libraries():
        return {}'''
                        )
                    
                    if new_content != content:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        files_fixed += 1
                        print(f"✓ Added import fallbacks to: {file_path}")
                
                except Exception as e:
                    print(f"⚠ Error processing {file_path}: {e}")
    
    return files_fixed

def fix_os_getenv_issues():
    """إصلاح مشاكل os.getenv None values"""
    files_fixed = 0
    
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('settings.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    new_content = content
                    
                    # إصلاح dj_database_url.parse(os.getenv('DATABASE_URL', ''))
                    if "os.getenv('DATABASE_URL', '')" in content:
                        new_content = new_content.replace(
                            "dj_database_url.parse(os.getenv('DATABASE_URL', ''))",
                            "dj_database_url.parse(os.getenv('DATABASE_URL') or 'sqlite:///db.sqlite3')"
                        )
                    
                    if new_content != content:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        files_fixed += 1
                        print(f"✓ Fixed os.getenv issues in: {file_path}")
                
                except Exception as e:
                    print(f"⚠ Error processing {file_path}: {e}")
    
    return files_fixed

def main():
    print("🔧 Starting Django relationship and import issues fix...")
    
    total_fixed = 0
    
    print("\n1️⃣ Adding TYPE_CHECKING imports...")
    total_fixed += add_type_checking_imports()
    
    print("\n2️⃣ Adding relationship type hints...")
    total_fixed += add_relationship_type_hints()
    
    print("\n3️⃣ Fixing specific relationship issues...")
    total_fixed += fix_specific_relationship_issues()
    
    print("\n4️⃣ Adding import fallbacks...")
    total_fixed += add_import_fallbacks()
    
    print("\n5️⃣ Fixing os.getenv issues...")
    total_fixed += fix_os_getenv_issues()
    
    print(f"\n✅ Fixed {total_fixed} files total!")

if __name__ == "__main__":
    main()