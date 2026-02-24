#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
تحليل شامل لقاعدة البيانات
Database Comprehensive Analysis Tool
"""

import sqlite3
import os
import sys

def analyze_database():
    db_path = 'db.sqlite3'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print('=' * 70)
    print('تحليل قاعدة البيانات الشامل - Tony ERP')
    print('=' * 70)

    # حجم الملف
    size_mb = os.path.getsize(db_path) / (1024 * 1024)
    print(f'\n📊 حجم قاعدة البيانات: {size_mb:.2f} MB')

    # عدد الجداول
    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
    table_count = cursor.fetchone()[0]
    print(f'📋 عدد الجداول: {table_count}')

    # عدد الفهارس
    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='index'")
    index_count = cursor.fetchone()[0]
    print(f'🔍 عدد الفهارس: {index_count}')

    # أكبر 10 جداول
    print('\n' + '=' * 70)
    print('أكبر 10 جداول من حيث عدد السجلات:')
    print('=' * 70)

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = cursor.fetchall()

    table_sizes = []
    for (table_name,) in tables:
        try:
            cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
            count = cursor.fetchone()[0]
            table_sizes.append((table_name, count))
        except Exception as e:
            pass

    table_sizes.sort(key=lambda x: x[1], reverse=True)
    total_records = sum(count for _, count in table_sizes)
    print(f'إجمالي السجلات: {total_records:,}\n')
    
    for i, (name, count) in enumerate(table_sizes[:15], 1):
        percentage = (count / total_records * 100) if total_records > 0 else 0
        bar = '█' * int(percentage / 2)
        print(f'{i:2}. {name:45} {count:>8,} ({percentage:5.1f}%) {bar}')

    # تحليل الفهارس لكل جدول
    print('\n' + '=' * 70)
    print('تحليل الفهارس:')
    print('=' * 70)

    cursor.execute("""
        SELECT tbl_name, COUNT(*) as idx_count 
        FROM sqlite_master 
        WHERE type='index' 
        GROUP BY tbl_name 
        ORDER BY idx_count DESC
        LIMIT 10
    """)
    indexed_tables = cursor.fetchall()
    
    print('\nالجداول الأكثر فهرسة:')
    for tbl, cnt in indexed_tables:
        print(f'  {tbl}: {cnt} فهرس')

    # الجداول بدون فهارس كافية
    print('\n' + '=' * 70)
    print('جداول كبيرة تحتاج فهارس إضافية:')
    print('=' * 70)

    tables_with_indexes = {}
    cursor.execute("SELECT tbl_name, COUNT(*) FROM sqlite_master WHERE type='index' GROUP BY tbl_name")
    for tbl, cnt in cursor.fetchall():
        tables_with_indexes[tbl] = cnt

    needs_index = []
    for name, count in table_sizes:
        if count > 50:  # جداول بها أكثر من 50 سجل
            idx_count = tables_with_indexes.get(name, 0)
            if idx_count < 2:  # أقل من 2 فهرس
                needs_index.append((name, count, idx_count))

    for name, count, idx_count in needs_index[:15]:
        print(f'⚠️  {name:45} السجلات: {count:>6,}  الفهارس: {idx_count}')

    # تحليل العلاقات (Foreign Keys)
    print('\n' + '=' * 70)
    print('تحليل العلاقات (Foreign Keys):')
    print('=' * 70)

    fk_count = 0
    tables_with_fk = 0
    for (table_name,) in tables:
        cursor.execute(f'PRAGMA foreign_key_list("{table_name}")')
        fks = cursor.fetchall()
        if fks:
            tables_with_fk += 1
            fk_count += len(fks)

    print(f'عدد العلاقات الأجنبية: {fk_count}')
    print(f'عدد الجداول بعلاقات: {tables_with_fk}')

    # فحص سلامة قاعدة البيانات
    print('\n' + '=' * 70)
    print('فحص سلامة قاعدة البيانات:')
    print('=' * 70)

    cursor.execute("PRAGMA integrity_check")
    integrity = cursor.fetchone()[0]
    if integrity == 'ok':
        print('✅ قاعدة البيانات سليمة')
    else:
        print(f'❌ مشكلة في السلامة: {integrity}')

    cursor.execute("PRAGMA quick_check")
    quick = cursor.fetchone()[0]
    if quick == 'ok':
        print('✅ الفحص السريع: سليم')
    else:
        print(f'❌ الفحص السريع: {quick}')

    # إحصائيات الأداء
    print('\n' + '=' * 70)
    print('إحصائيات قاعدة البيانات:')
    print('=' * 70)

    cursor.execute("PRAGMA page_count")
    page_count = cursor.fetchone()[0]
    
    cursor.execute("PRAGMA page_size")
    page_size = cursor.fetchone()[0]
    
    cursor.execute("PRAGMA freelist_count")
    freelist = cursor.fetchone()[0]

    print(f'عدد الصفحات: {page_count:,}')
    print(f'حجم الصفحة: {page_size:,} bytes')
    print(f'الصفحات الحرة: {freelist:,}')
    print(f'المساحة المهدرة: {(freelist * page_size / 1024):.2f} KB')

    # تحليل أعمدة الجداول الرئيسية
    print('\n' + '=' * 70)
    print('تحليل الجداول الرئيسية:')
    print('=' * 70)

    main_tables = [name for name, count in table_sizes[:10]]
    
    for table_name in main_tables[:5]:
        cursor.execute(f'PRAGMA table_info("{table_name}")')
        columns = cursor.fetchall()
        print(f'\n📋 {table_name} ({len(columns)} عمود):')
        
        nullable_count = sum(1 for col in columns if col[3] == 0)
        print(f'   - أعمدة قابلة للـ NULL: {nullable_count}')
        
        # فحص الفهارس
        cursor.execute(f'PRAGMA index_list("{table_name}")')
        indexes = cursor.fetchall()
        print(f'   - الفهارس: {len(indexes)}')

    conn.close()
    print('\n' + '=' * 70)
    print('✅ اكتمل التحليل')
    print('=' * 70)

if __name__ == '__main__':
    analyze_database()
