#!/usr/bin/env python3
"""
سكريبت لفحص صحة روابط القائمة الجانبية (Sidebar)
يقوم بالتحقق من:
1. الروابط المعطلة
2. الروابط المكررة
3. الروابط بدون URL names
"""
import os
import sys
import re
from collections import Counter

# إعداد Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')

import django
django.setup()

from django.urls import reverse, NoReverseMatch
from colorama import init, Fore, Back, Style

# تفعيل الألوان
init(autoreset=True)

def extract_links_from_html(html_content):
    """استخراج الروابط من HTML"""
    
    # استخراج data-url-name
    url_names_pattern = r'data-url-name="([^"]+)"'
    url_names = re.findall(url_names_pattern, html_content)
    
    # استخراج href مباشر
    href_pattern = r'href="(/[^"]+)"'
    direct_hrefs = re.findall(href_pattern, html_content)
    
    # استخراج أسماء الوحدات
    module_pattern = r'data-module="([^"]+)"'
    modules = re.findall(module_pattern, html_content)
    
    return {
        'url_names': url_names,
        'direct_hrefs': direct_hrefs,
        'modules': modules
    }

def check_url_names(url_names):
    """فحص صحة URL names"""
    
    print(f"\n{Fore.CYAN}{'='*70}")
    print(f"{Fore.CYAN}🔍 فحص URL Names")
    print(f"{Fore.CYAN}{'='*70}\n")
    
    working_links = []
    broken_links = []
    
    for url_name in set(url_names):  # استخدام set لتجنب التكرار في الفحص
        try:
            url = reverse(url_name)
            working_links.append(url_name)
            print(f"{Fore.GREEN}✅ {url_name:<50} → {url}")
        except NoReverseMatch:
            broken_links.append(url_name)
            print(f"{Fore.RED}❌ {url_name:<50} → NOT FOUND")
        except Exception as e:
            broken_links.append(url_name)
            print(f"{Fore.YELLOW}⚠️  {url_name:<50} → ERROR: {str(e)[:30]}")
    
    return working_links, broken_links

def check_duplicates(items, item_type="items"):
    """فحص التكرارات"""
    
    print(f"\n{Fore.CYAN}{'='*70}")
    print(f"{Fore.CYAN}🔄 فحص التكرارات - {item_type}")
    print(f"{Fore.CYAN}{'='*70}\n")
    
    counter = Counter(items)
    duplicates = {item: count for item, count in counter.items() if count > 1}
    
    if duplicates:
        print(f"{Fore.YELLOW}⚠️  وجدت {len(duplicates)} عنصر مكرر:\n")
        for item, count in sorted(duplicates.items(), key=lambda x: x[1], reverse=True):
            print(f"{Fore.YELLOW}   🔄 {item:<50} (تكرر {count} مرة)")
    else:
        print(f"{Fore.GREEN}✅ لا توجد تكرارات")
    
    return duplicates

def analyze_sidebar(html_content):
    """تحليل شامل للـ Sidebar"""
    
    print(f"\n{Fore.MAGENTA}{Back.WHITE}{'='*70}")
    print(f"{Fore.MAGENTA}{Back.WHITE} 📊 تحليل شامل للقائمة الجانبية (Sidebar)")
    print(f"{Fore.MAGENTA}{Back.WHITE}{'='*70}\n")
    
    # استخراج البيانات
    links = extract_links_from_html(html_content)
    
    # 1. فحص URL Names
    working_links, broken_links = check_url_names(links['url_names'])
    
    # 2. فحص التكرارات في URL Names
    url_duplicates = check_duplicates(links['url_names'], "URL Names")
    
    # 3. فحص التكرارات في الوحدات
    module_duplicates = check_duplicates(links['modules'], "Modules")
    
    # 4. تحليل الروابط المباشرة
    print(f"\n{Fore.CYAN}{'='*70}")
    print(f"{Fore.CYAN}📝 الروابط المباشرة (Direct HREFs)")
    print(f"{Fore.CYAN}{'='*70}\n")
    
    direct_links = [href for href in links['direct_hrefs'] if not href.startswith('/static') and not href.startswith('/media')]
    
    if direct_links:
        print(f"{Fore.YELLOW}⚠️  وجدت {len(set(direct_links))} رابط مباشر (يُفضل تحويلها إلى URL names):\n")
        for href in sorted(set(direct_links)):
            print(f"{Fore.YELLOW}   📌 {href}")
    else:
        print(f"{Fore.GREEN}✅ لا توجد روابط مباشرة (ممتاز!)")
    
    # 5. النتيجة النهائية
    print(f"\n{Fore.MAGENTA}{Back.WHITE}{'='*70}")
    print(f"{Fore.MAGENTA}{Back.WHITE} 📊 النتائج النهائية")
    print(f"{Fore.MAGENTA}{Back.WHITE}{'='*70}\n")
    
    total_url_names = len(set(links['url_names']))
    total_modules = len(set(links['modules']))
    
    print(f"{Fore.CYAN}📌 إحصائيات عامة:")
    print(f"   • إجمالي URL Names: {Fore.WHITE}{total_url_names}")
    print(f"   • إجمالي الوحدات: {Fore.WHITE}{total_modules}")
    print(f"   • إجمالي الروابط المباشرة: {Fore.WHITE}{len(set(direct_links))}\n")
    
    print(f"{Fore.GREEN}✅ الروابط الصحيحة:")
    print(f"   • عدد الروابط الصحيحة: {Fore.WHITE}{len(working_links)}")
    print(f"   • نسبة النجاح: {Fore.WHITE}{len(working_links)/total_url_names*100:.1f}%\n")
    
    if broken_links:
        print(f"{Fore.RED}❌ الروابط المعطلة:")
        print(f"   • عدد الروابط المعطلة: {Fore.WHITE}{len(broken_links)}")
        print(f"   • نسبة الفشل: {Fore.WHITE}{len(broken_links)/total_url_names*100:.1f}%\n")
    
    if url_duplicates:
        print(f"{Fore.YELLOW}🔄 التكرارات:")
        print(f"   • عدد URL Names المكررة: {Fore.WHITE}{len(url_duplicates)}")
        print(f"   • إجمالي التكرارات: {Fore.WHITE}{sum(url_duplicates.values())}\n")
    
    # 6. التوصيات
    print(f"{Fore.MAGENTA}{'='*70}")
    print(f"{Fore.MAGENTA}💡 التوصيات")
    print(f"{Fore.MAGENTA}{'='*70}\n")
    
    if broken_links:
        print(f"{Fore.RED}🔧 أولوية عالية:")
        print(f"{Fore.YELLOW}   1. أصلح الروابط المعطلة ({len(broken_links)} رابط)")
    
    if url_duplicates:
        print(f"{Fore.YELLOW}🔧 أولوية متوسطة:")
        print(f"{Fore.YELLOW}   2. احذف الروابط المكررة ({len(url_duplicates)} رابط)")
    
    if direct_links:
        print(f"{Fore.CYAN}🔧 أولوية منخفضة:")
        print(f"{Fore.YELLOW}   3. حوّل الروابط المباشرة إلى URL names ({len(set(direct_links))} رابط)")
    
    if not broken_links and not url_duplicates and not direct_links:
        print(f"{Fore.GREEN}🎉 ممتاز! القائمة الجانبية منظمة بشكل مثالي!")
    
    print()

def main():
    """الدالة الرئيسية"""
    
    # قراءة محتوى من الكود المُرسل (يمكن تعديله لقراءة من ملف)
    # في الوضع الحقيقي، اقرأ من ملف HTML
    
    # للاختبار، سنستخدم نموذج بسيط
    sample_html = """
    <a href="/dashboard/" data-url-name="core:dashboard">Dashboard</a>
    <a href="/accounting/" data-url-name="accounting:dashboard">Accounting</a>
    <a href="/accounting/" data-url-name="accounting:dashboard">Accounting Duplicate</a>
    <a href="/sales/" data-url-name="sales:invoice_list">Sales</a>
    <a href="/invalid/" data-url-name="invalid:not_exists">Invalid</a>
    <a href="/direct-link/">Direct Link</a>
    <li class="sidebar-group" data-module="accounting">Accounting</li>
    <li class="sidebar-group" data-module="sales">Sales</li>
    """
    
    print(f"\n{Fore.CYAN}ℹ️  ملاحظة: هذا مثال للاختبار. للاستخدام الفعلي:")
    print(f"{Fore.YELLOW}   1. انسخ كود HTML الكامل")
    print(f"{Fore.YELLOW}   2. احفظه في ملف (مثلاً: sidebar.html)")
    print(f"{Fore.YELLOW}   3. عدّل السكريبت لقراءة من الملف\n")
    
    # تحليل
    analyze_sidebar(sample_html)
    
    print(f"\n{Fore.GREEN}✨ انتهى التحليل!")
    print(f"{Fore.CYAN}📄 راجع التقرير الكامل في: {Fore.WHITE}SIDEBAR_ANALYSIS_REPORT.md\n")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}⚠️  تم إيقاف السكريبت بواسطة المستخدم")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Fore.RED}❌ خطأ: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
