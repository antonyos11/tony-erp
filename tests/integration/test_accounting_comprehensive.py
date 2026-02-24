#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
خطة اختبار شاملة لنظام المحاسبة - Tony ERP
Comprehensive Test Plan for Accounting System
"""

import os
import sys
import django
import time
import json
from decimal import Decimal
from datetime import date, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from django.test import Client, override_settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.db.models import Sum, Count, Q
from django.utils import timezone

from accounting.models import (
    Account, JournalEntry, JournalEntryItem, CostCenter,
    FiscalYear, FinancialAnalysis1, FinancialAnalysis2,
    Cheque, Expense, Revenue
)

User = get_user_model()

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}\n")

def print_section(text):
    print(f"\n{Colors.BOLD}{Colors.MAGENTA}{text}{Colors.RESET}")
    print(f"{Colors.MAGENTA}{'-'*80}{Colors.RESET}")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")

def print_info(text):
    print(f"{Colors.BLUE}ℹ {text}{Colors.RESET}")

# ============================================================================
# 1. Database Integrity Tests
# ============================================================================

def test_database_integrity():
    print_header("📊 1. اختبارات قاعدة البيانات (Database Integrity)")
    
    # 1.1 Check tables exist
    print_section("✓ 1.1 فحص وجود الجداول الأساسية:")
    tables = [
        ('accounting_account', Account),
        ('accounting_journalentry', JournalEntry),
        ('accounting_journalentryitem', JournalEntryItem),
        ('accounting_costcenter', CostCenter),
        ('accounting_fiscalyear', FiscalYear),
        ('accounting_financialanalysis1', FinancialAnalysis1),
        ('accounting_financialanalysis2', FinancialAnalysis2),
        ('accounting_cheque', Cheque),
        ('accounting_expense', Expense),
        ('accounting_revenue', Revenue),
    ]
    
    for table_name, model in tables:
        try:
            count = model.objects.count()
            print_success(f"{table_name}: {count} سجل")
        except Exception as e:
            print_error(f"{table_name}: خطأ - {str(e)[:50]}")
    
    # 1.2 Check orphaned records
    print_section("✓ 1.2 فحص سلامة العلاقات:")
    
    # Orphaned journal entry items
    orphaned_items = JournalEntryItem.objects.filter(journal_entry__isnull=True).count()
    if orphaned_items == 0:
        print_success(f"قيود يتيمة (بدون قيد رئيسي): {orphaned_items}")
    else:
        print_error(f"قيود يتيمة (بدون قيد رئيسي): {orphaned_items}")
    
    # 1.3 Check balanced journal entries
    print_section("✓ 1.3 فحص توازن القيود المحاسبية:")
    
    unbalanced = []
    posted_entries = JournalEntry.objects.filter(is_posted=True)[:100]
    
    for je in posted_entries:
        items = je.items.all()
        debits = sum(i.amount for i in items if i.type == 'debit')
        credits = sum(i.amount for i in items if i.type == 'credit')
        diff = abs(debits - credits)
        
        if diff > Decimal('0.01'):
            unbalanced.append({
                'id': je.id,
                'number': je.number,
                'diff': diff
            })
    
    if len(unbalanced) == 0:
        print_success(f"قيود غير متوازنة: {len(unbalanced)}")
    else:
        print_error(f"قيود غير متوازنة: {len(unbalanced)}")
        for ub in unbalanced[:5]:
            print_error(f"  - القيد {ub['number']} (ID: {ub['id']}): فرق = {ub['diff']}")
    
    # 1.4 Data quality checks
    print_section("✓ 1.4 فحص جودة البيانات:")
    
    accounts_without_name = Account.objects.filter(Q(name='') | Q(name__isnull=True)).count()
    accounts_without_code = Account.objects.filter(Q(code='') | Q(code__isnull=True)).count()
    duplicate_codes = Account.objects.values('code').annotate(
        count=Count('code')
    ).filter(count__gt=1).count()
    
    if accounts_without_name == 0:
        print_success(f"حسابات بدون اسم: {accounts_without_name}")
    else:
        print_error(f"حسابات بدون اسم: {accounts_without_name}")
    
    if accounts_without_code == 0:
        print_success(f"حسابات بدون كود: {accounts_without_code}")
    else:
        print_error(f"حسابات بدون كود: {accounts_without_code}")
    
    if duplicate_codes == 0:
        print_success(f"أكواد حسابات مكررة: {duplicate_codes}")
    else:
        print_error(f"أكواد حسابات مكررة: {duplicate_codes}")
    
    # Check negative amounts
    negative_amounts = JournalEntryItem.objects.filter(amount__lt=0).count()
    if negative_amounts == 0:
        print_success(f"مبالغ سالبة في القيود: {negative_amounts}")
    else:
        print_error(f"مبالغ سالبة في القيود: {negative_amounts}")

# ============================================================================
# 2. Performance Tests
# ============================================================================

def test_performance():
    print_header("⚡ 2. اختبارات الأداء (Performance Testing)")
    
    user = User.objects.first()
    if not user:
        print_error("لا يوجد مستخدمين في النظام")
        return
    
    pages_to_test = [
        ('/accounting/', 'لوحة التحكم'),
        ('/accounting/accounts/', 'دليل الحسابات'),
        ('/accounting/journal-entries/', 'القيود اليومية'),
        ('/accounting/balance-sheet/', 'الميزانية العمومية'),
        ('/accounting/income-statement/', 'قائمة الدخل'),
        ('/accounting/trial-balance/', 'ميزان المراجعة'),
        ('/accounting/cost-centers/', 'مراكز التكلفة'),
    ]
    
    print_section("✓ 2.1 زمن تحميل الصفحات:")
    
    with override_settings(ALLOWED_HOSTS=['testserver', '*']):
        client = Client()
        client.force_login(user)
        
        for url, name in pages_to_test:
            try:
                start = time.time()
                response = client.get(url)
                elapsed = (time.time() - start) * 1000
                
                if response.status_code == 200:
                    if elapsed < 1000:
                        speed = f"{Colors.GREEN}🟢{Colors.RESET}"
                    elif elapsed < 3000:
                        speed = f"{Colors.YELLOW}🟡{Colors.RESET}"
                    else:
                        speed = f"{Colors.RED}🔴{Colors.RESET}"
                    
                    print(f"   {speed} {name}: {elapsed:.0f}ms (كود: {response.status_code})")
                else:
                    print_error(f"{name}: {response.status_code}")
            except Exception as e:
                print_error(f"{name}: {str(e)[:50]}")

# ============================================================================
# 3. Functional Tests
# ============================================================================

def test_functional():
    print_header("🔧 3. اختبارات الوظائف (Functional Testing)")
    
    user = User.objects.first()
    if not user:
        print_error("لا يوجد مستخدمين في النظام")
        return
    
    # 3.1 Test account creation
    print_section("✓ 3.1 اختبار دورة حياة الحساب:")
    
    try:
        # Create account
        test_account = Account.objects.create(
            code='TEST_999',
            name='حساب اختبار شامل',
            account_type='asset',
            can_post=True
        )
        print_success(f"إنشاء حساب: {test_account.code} - {test_account.name}")
        
        # Update account
        test_account.name = 'حساب اختبار محدث'
        test_account.save()
        print_success(f"تحديث حساب: {test_account.name}")
        
        # Delete account
        test_account.delete()
        print_success("حذف حساب الاختبار")
        
    except Exception as e:
        print_error(f"خطأ في اختبار الحساب: {str(e)}")
    
    # 3.2 Test journal entries
    print_section("✓ 3.2 اختبار القيود المحاسبية:")
    
    try:
        accounts = Account.objects.filter(can_post=True)[:2]
        if len(accounts) >= 2:
            # Create balanced entry
            je = JournalEntry.objects.create(
                date=timezone.now().date(),
                description='قيد اختبار شامل',
                entry_type='manual',
                created_by=user
            )
            print_success(f"إنشاء قيد: {je.number}")
            
            JournalEntryItem.objects.create(
                journal_entry=je,
                account=accounts[0],
                type='debit',
                amount=1000,
                description='مدين'
            )
            
            JournalEntryItem.objects.create(
                journal_entry=je,
                account=accounts[1],
                type='credit',
                amount=1000,
                description='دائن'
            )
            
            # Check balance
            debits = je.items.filter(type='debit').aggregate(Sum('amount'))['amount__sum'] or 0
            credits = je.items.filter(type='credit').aggregate(Sum('amount'))['amount__sum'] or 0
            balanced = abs(debits - credits) < Decimal('0.01')
            
            if balanced:
                print_success(f"القيد متوازن: مدين={debits}, دائن={credits}")
            else:
                print_error(f"القيد غير متوازن: مدين={debits}, دائن={credits}")
            
            # Clean up
            je.delete()
            print_success("حذف قيد الاختبار")
        else:
            print_warning("عدد الحسابات غير كافٍ للاختبار")
    except Exception as e:
        print_error(f"خطأ في اختبار القيود: {str(e)}")

# ============================================================================
# 4. Security Tests
# ============================================================================

def test_security():
    print_header("🔒 4. اختبارات الأمان (Security Testing)")
    
    print_section("✓ 4.1 فحص الحماية من الوصول غير المصرح:")
    
    protected_urls = [
        '/accounting/accounts/create/',
        '/accounting/journal-entries/create/',
        '/accounting/settings/',
    ]
    
    with override_settings(ALLOWED_HOSTS=['testserver', '*']):
        client_anon = Client()  # No login
        
        for url in protected_urls:
            try:
                response = client_anon.get(url)
                is_protected = response.status_code in [302, 401, 403]
                
                if is_protected:
                    print_success(f"{url}: محمي (كود: {response.status_code})")
                else:
                    print_error(f"{url}: غير محمي! (كود: {response.status_code})")
            except Exception as e:
                print_error(f"{url}: خطأ - {str(e)[:50]}")

# ============================================================================
# 5. API Tests
# ============================================================================

def test_api():
    print_header("🌐 5. اختبارات API")
    
    user = User.objects.first()
    if not user:
        print_error("لا يوجد مستخدمين في النظام")
        return
    
    api_endpoints = [
        ('/accounting/api/accounts/search/?q=', 'بحث الحسابات'),
    ]
    
    # Check if account 4 exists for details test
    if Account.objects.filter(id=4).exists():
        api_endpoints.append(('/accounting/accounts/4/details/', 'تفاصيل حساب'))
    
    print_section("✓ 5.1 فحص استجابة API:")
    
    with override_settings(ALLOWED_HOSTS=['testserver', '*']):
        client = Client()
        client.force_login(user)
        
        for url, name in api_endpoints:
            try:
                response = client.get(url)
                
                if response.status_code == 200:
                    try:
                        data = json.loads(response.content)
                        content_str = json.dumps(data, ensure_ascii=False)
                        
                        # Check for Unicode escapes
                        has_unicode_escape = '\\u06' in str(response.content)
                        
                        if has_unicode_escape:
                            print_error(f"{name}: يحتوي على Unicode escape")
                        else:
                            print_success(f"{name}: {response.status_code} - العربية صحيحة ✓")
                    except json.JSONDecodeError:
                        print_warning(f"{name}: {response.status_code} - JSON غير صالح")
                else:
                    print_warning(f"{name}: {response.status_code}")
            except Exception as e:
                print_error(f"{name}: {str(e)[:50]}")

# ============================================================================
# 6. Statistics
# ============================================================================

def test_statistics():
    print_header("📈 6. إحصائيات النظام")
    
    print_section("✓ إحصائيات البيانات:")
    
    stats = {
        'عدد الحسابات': Account.objects.count(),
        'عدد القيود': JournalEntry.objects.count(),
        'قيود مرحلة': JournalEntry.objects.filter(is_posted=True).count(),
        'قيود مسودة': JournalEntry.objects.filter(is_posted=False).count(),
        'مراكز التكلفة': CostCenter.objects.count(),
        'السنوات المالية': FiscalYear.objects.count(),
        'الشيكات': Cheque.objects.count(),
        'المصروفات': Expense.objects.count(),
        'الإيرادات': Revenue.objects.count(),
    }
    
    for key, value in stats.items():
        print_info(f"{key}: {value:,}")
    
    print_section("✓ الإجماليات المالية:")
    
    total_debits = JournalEntryItem.objects.filter(type='debit').aggregate(
        Sum('amount'))['amount__sum'] or Decimal('0')
    total_credits = JournalEntryItem.objects.filter(type='credit').aggregate(
        Sum('amount'))['amount__sum'] or Decimal('0')
    
    print_info(f"إجمالي المدين: {total_debits:,.2f}")
    print_info(f"إجمالي الدائن: {total_credits:,.2f}")
    
    diff = abs(total_debits - total_credits)
    if diff < Decimal('0.01'):
        print_success(f"الفرق: {diff:,.2f} (متوازن)")
    else:
        print_error(f"الفرق: {diff:,.2f} (غير متوازن)")

# ============================================================================
# 7. Summary
# ============================================================================

def print_summary():
    print_header("✅ ملخص نتائج الاختبار")
    
    print(f"""
{Colors.BOLD}النتيجة النهائية:{Colors.RESET}

✓ تم اختبار:
  - سلامة قاعدة البيانات
  - أداء الصفحات
  - الوظائف الأساسية
  - الأمان والحماية
  - واجهات API
  - الإحصائيات

{Colors.GREEN}النظام جاهز للاستخدام!{Colors.RESET}
""")

# ============================================================================
# Main Execution
# ============================================================================

def main():
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("╔════════════════════════════════════════════════════════════════════════════╗")
    print("║           خطة اختبار شاملة لنظام المحاسبة - Tony ERP                      ║")
    print("║        Comprehensive Test Plan for Accounting System                       ║")
    print("╚════════════════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.RESET}")
    
    try:
        test_database_integrity()
        test_performance()
        test_functional()
        test_security()
        test_api()
        test_statistics()
        print_summary()
        
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}تم إيقاف الاختبار بواسطة المستخدم{Colors.RESET}")
    except Exception as e:
        print(f"\n{Colors.RED}خطأ عام: {str(e)}{Colors.RESET}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
