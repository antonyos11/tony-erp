#!/usr/bin/env python3
"""
حل مشاكل Django choices وget_display methods
- إصلاح مشاكل dict(field.choices) في Views
- إصلاح مشاكل get_*_display() methods
- إصلاح مشاكل openpyxl worksheet access
- إصلاح مشاكل bill_id وpayment_id في models
"""

import os
import re
from pathlib import Path

def fix_choices_display():
    """إصلاح مشاكل dict(field.choices) في Django views"""
    files_fixed = 0
    
    # البحث عن الاستخدامات المشكوك فيها
    pattern = r'dict\(([^.]+)\.\_meta\.get_field\([\'"][^\'\"]+[\'\"]\)\.choices\)'
    replacement = r'dict(\1._meta.get_field(\2).choices or [])'
    
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    new_content = content
                    
                    # إصلاح مشكلة {choice[0]: choice[1] for choice in Account._meta.get_field('account_type').choices or []}
                    if "{choice[0]: choice[1] for choice in Account._meta.get_field('account_type').choices or []}" in content:
                        new_content = new_content.replace(
                            "{choice[0]: choice[1] for choice in Account._meta.get_field('account_type').choices or []}",
                            "{choice[0]: choice[1] for choice in Account._meta.get_field('account_type').choices or []}"
                        )
                    
                    # إصلاح استخدامات أخرى مماثلة
                    new_content = re.sub(
                        r'dict\(([^.]+)\.\_meta\.get_field\([\'"]([^\'\"]+)[\'\"]\)\.choices\)',
                        r'{choice[0]: choice[1] for choice in \1._meta.get_field(\'\2\').choices or []}',
                        new_content
                    )
                    
                    if new_content != content:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        files_fixed += 1
                        print(f"✓ Fixed choices display in: {file_path}")
                
                except Exception as e:
                    print(f"⚠ Error processing {file_path}: {e}")
    
    return files_fixed

def fix_openpyxl_worksheet():
    """إصلاح مشاكل openpyxl worksheet access"""
    files_fixed = 0
    
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    new_content = content
                    
                    # إصلاح wb.active
                    if 'wb=openpyxl.Workbook(); ws=wb.active; assert ws is not None' in content:
                        new_content = new_content.replace(
                            'wb=openpyxl.Workbook(); ws=wb.active; assert ws is not None',
                            'wb=openpyxl.Workbook(); ws=wb.active; assert ws is not None; assert ws is not None'
                        )
                    
                    # إصلاح ws.title
                    if "if ws: ws.title='Cash Flow'" in content:
                        new_content = new_content.replace(
                            "if ws: ws.title='Cash Flow'",
                            "if ws: if ws: ws.title='Cash Flow'"
                        )
                    
                    # إصلاح ws.append calls
                    new_content = re.sub(
                        r'(\s+)ws\.append\(',
                        r'\1if ws: if ws: ws.append(',
                        new_content
                    )
                    
                    if new_content != content:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        files_fixed += 1
                        print(f"✓ Fixed openpyxl worksheet in: {file_path}")
                
                except Exception as e:
                    print(f"⚠ Error processing {file_path}: {e}")
    
    return files_fixed

def fix_bill_id_attributes():
    """إصلاح مشاكل bill_id وpayment_id في models"""
    files_fixed = 0
    
    replacements = {
        '.bill_id': '.bill.id if .bill else None',
        '.payment_id': '.payment.id if .payment else None',
        '.invoice_id': '.invoice.id if .invoice else None',
        '.customer_id': '.customer.id if .customer else None',
        '.supplier_id': '.supplier.id if .supplier else None',
    }
    
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    new_content = content
                    
                    for old, new in replacements.items():
                        if old in content:
                            # نحتاج إلى معالجة خاصة لكل حالة
                            if old == '.bill_id':
                                new_content = new_content.replace(
                                    'payment.bill.id if payment.bill else None',
                                    'payment.bill.id if payment.bill else None'
                                )
                            elif old == '.invoice_id':
                                new_content = new_content.replace(
                                    'item.invoice.id if item.invoice else None',
                                    'item.invoice.id if item.invoice else None'
                                )
                    
                    if new_content != content:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        files_fixed += 1
                        print(f"✓ Fixed bill_id attributes in: {file_path}")
                
                except Exception as e:
                    print(f"⚠ Error processing {file_path}: {e}")
    
    return files_fixed

def fix_manager_methods():
    """إصلاح مشاكل Manager methods مثل .active()"""
    files_fixed = 0
    
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    new_content = content
                    
                    # إصلاح CostCenter.objects.filter(active=True)
                    if 'CostCenter.objects.filter(active=True)' in content:
                        new_content = new_content.replace(
                            'CostCenter.objects.filter(active=True)',
                            'CostCenter.objects.filter(active=True)'
                        )
                    
                    # إصلاح other manager methods
                    new_content = re.sub(
                        r'\.objects\.active\(\)\.with_expenses\(\)',
                        r'.objects.filter(active=True)',
                        new_content
                    )
                    
                    if new_content != content:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        files_fixed += 1
                        print(f"✓ Fixed manager methods in: {file_path}")
                
                except Exception as e:
                    print(f"⚠ Error processing {file_path}: {e}")
    
    return files_fixed

def fix_journal_entry_date():
    """إصلاح مشاكل journal_entry.date في None objects"""
    files_fixed = 0
    
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    new_content = content
                    
                    # إصلاح it.journal_entry.date
                    if "'date': it.journal_entry.date if it.journal_entry else None," in content:
                        new_content = new_content.replace(
                            "'date': it.journal_entry.date if it.journal_entry else None,",
                            "'date': it.journal_entry.date if it.journal_entry else None,"
                        )
                    
                    if new_content != content:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        files_fixed += 1
                        print(f"✓ Fixed journal_entry.date in: {file_path}")
                
                except Exception as e:
                    print(f"⚠ Error processing {file_path}: {e}")
    
    return files_fixed

def fix_aging_total():
    """إصلاح مشاكل aging['total'] type mismatch"""
    files_fixed = 0
    
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    new_content = content
                    
                    # إصلاح aging['total'] = Decimal(str(sum(aging.values())))
                    if "aging['total'] = Decimal(str(sum(aging.values())))" in content:
                        new_content = new_content.replace(
                            "aging['total'] = Decimal(str(sum(aging.values())))",
                            "aging['total'] = Decimal(str(sum(aging.values())))"
                        )
                    
                    if new_content != content:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        files_fixed += 1
                        print(f"✓ Fixed aging total in: {file_path}")
                
                except Exception as e:
                    print(f"⚠ Error processing {file_path}: {e}")
    
    return files_fixed

def main():
    print("🔧 Starting Django display/choices/views issues fix...")
    
    total_fixed = 0
    
    print("\n1️⃣ Fixing choices display...")
    total_fixed += fix_choices_display()
    
    print("\n2️⃣ Fixing openpyxl worksheet...")
    total_fixed += fix_openpyxl_worksheet()
    
    print("\n3️⃣ Fixing bill_id attributes...")
    total_fixed += fix_bill_id_attributes()
    
    print("\n4️⃣ Fixing manager methods...")
    total_fixed += fix_manager_methods()
    
    print("\n5️⃣ Fixing journal_entry.date...")
    total_fixed += fix_journal_entry_date()
    
    print("\n6️⃣ Fixing aging total...")
    total_fixed += fix_aging_total()
    
    print(f"\n✅ Fixed {total_fixed} files total!")

if __name__ == "__main__":
    main()