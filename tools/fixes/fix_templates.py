"""
سكريبت إصلاح القوالب المتأثرة من الترقية السابقة
يقوم بإصلاح الأقواس المزدوجة في CSS دون تأثير على متغيرات Django
"""
import os
import re
from pathlib import Path

TEMPLATES_DIR = Path(r"H:\برمجة\الشامل\الشامل\الشامل\app\templates")

def fix_template(filepath):
    """Fix CSS double braces while preserving Django template variables"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # Fix missing closing braces in Django variables (caused by previous buggy fix)
    # Pattern: {{ something } -> {{ something }}
    content = re.sub(r'\{\{\s*([^{}]+?)\s*\}(?!\})', r'{{ \1 }}', content)
    
    # Now fix CSS double braces inside <style> tags
    def fix_style_block(match):
        style_content = match.group(1)
        # Replace {{ with { and }} with } but NOT {{ variable }} patterns
        # First, protect Django variables by replacing them with placeholders
        placeholders = {}
        counter = [0]
        
        def save_var(m):
            key = f"__DJANGO_VAR_{counter[0]}__"
            placeholders[key] = m.group(0)
            counter[0] += 1
            return key
        
        # Protect Django variables: {{ anything }}
        protected = re.sub(r'\{\{\s*[a-zA-Z_][a-zA-Z0-9_.|:\'\"=\s]*\s*\}\}', save_var, style_content)
        
        # Now replace remaining {{ }} in CSS with { }
        fixed = protected.replace('{{', '{').replace('}}', '}')
        
        # Restore Django variables
        for key, value in placeholders.items():
            fixed = fixed.replace(key, value)
        
        return f'<style>{fixed}</style>'
    
    # Apply fix to all style blocks
    content = re.sub(r'<style>(.*?)</style>', fix_style_block, content, flags=re.DOTALL)
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    print("=" * 60)
    print("سكريبت إصلاح القوالب")
    print("=" * 60)
    
    fixed_count = 0
    error_count = 0
    
    for filepath in TEMPLATES_DIR.rglob("*.html"):
        try:
            if fix_template(filepath):
                print(f"✅ تم إصلاح: {filepath.name}")
                fixed_count += 1
        except Exception as e:
            print(f"❌ خطأ في {filepath.name}: {e}")
            error_count += 1
    
    print("=" * 60)
    print(f"النتائج:")
    print(f"  - تم الإصلاح: {fixed_count}")
    print(f"  - أخطاء: {error_count}")
    print("=" * 60)

if __name__ == "__main__":
    main()
