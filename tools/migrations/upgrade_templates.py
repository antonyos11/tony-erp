"""
سكريبت تحديث القوالب القديمة إلى القالب الاحترافي
Upgrade old form templates to professional template
"""

import os
import re
from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent / 'templates'

# القوالب التي تحتاج تحديث (تستخدم extends 'base.html' وهي form)
OLD_EXTENDS_PATTERNS = [
    r"{% extends 'base\.html' %}",
    r'{% extends "base\.html" %}',
]

NEW_EXTENDS = "{% extends 'base_v2.html' %}"

# تحسينات CSS المشتركة
ENHANCED_STYLES = '''
<style>
    .form-hero {
        background: linear-gradient(135deg, #1e3a5f 0%, #2c5282 100%);
        border-radius: 20px;
        padding: 2rem;
        color: white;
        margin-bottom: 2rem;
        position: relative;
        overflow: hidden;
    }
    
    .form-hero::before {
        content: '';
        position: absolute;
        top: -50%;
        right: -20%;
        width: 300px;
        height: 300px;
        background: rgba(255,255,255,0.1);
        border-radius: 50%;
    }
    
    .form-hero h1 {
        font-size: 1.75rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        position: relative;
    }
    
    .form-card {
        background: var(--card-bg, white);
        border-radius: 16px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        overflow: hidden;
        border: 1px solid var(--border-color, #e5e7eb);
        animation: slideUp 0.4s ease;
    }
    
    @keyframes slideUp {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .form-section {
        padding: 1.5rem 2rem;
        border-bottom: 1px solid var(--border-color, #e5e7eb);
    }
    
    .form-section:last-child {
        border-bottom: none;
    }
    
    .section-title {
        font-size: 1rem;
        font-weight: 600;
        color: var(--primary-color, #1e3a5f);
        margin-bottom: 1.25rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .form-floating > .form-control,
    .form-floating > .form-select {
        height: calc(3.5rem + 2px);
        padding: 1rem 0.75rem;
        border-radius: 10px;
        border: 1.5px solid var(--border-color, #dee2e6);
        transition: all 0.3s ease;
    }
    
    .form-floating > .form-control:focus,
    .form-floating > .form-select:focus {
        border-color: var(--primary-color, #1e3a5f);
        box-shadow: 0 0 0 4px rgba(30, 58, 95, 0.1);
    }
    
    .form-actions {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 1.5rem 2rem;
        background: var(--light-bg, #f8fafc);
        border-top: 1px solid var(--border-color, #e5e7eb);
    }
    
    .btn-save {
        background: linear-gradient(135deg, #1e3a5f 0%, #2c5282 100%);
        color: white;
        border: none;
        padding: 0.875rem 2rem;
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .btn-save:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(30, 58, 95, 0.35);
        color: white;
    }
    
    .btn-cancel {
        background: transparent;
        color: #6c757d;
        border: 1.5px solid var(--border-color, #dee2e6);
        padding: 0.875rem 1.5rem;
        border-radius: 10px;
        transition: all 0.3s ease;
        text-decoration: none;
    }
    
    .btn-cancel:hover {
        background: var(--light-bg, #f8fafc);
    }
    
    .required-star {
        color: #e74c3c;
    }
    
    @media (max-width: 768px) {
        .form-hero { padding: 1.5rem; }
        .form-section { padding: 1.25rem; }
        .form-actions {
            flex-direction: column;
            gap: 1rem;
        }
        .form-actions .btn-save,
        .form-actions .btn-cancel {
            width: 100%;
            justify-content: center;
        }
    }
</style>
'''


def find_templates_to_upgrade():
    """البحث عن القوالب التي تحتاج تحديث"""
    templates_to_upgrade = []
    
    # البحث في كل أنواع القوالب
    patterns_to_search = ['*_form.html', '*_list.html', '*_detail.html', 'dashboard.html']
    
    for pattern in patterns_to_search:
        for html_file in TEMPLATES_DIR.rglob(pattern):
            try:
                content = html_file.read_text(encoding='utf-8')
                for old_pattern in OLD_EXTENDS_PATTERNS:
                    if re.search(old_pattern, content):
                        if html_file not in templates_to_upgrade:
                            templates_to_upgrade.append(html_file)
                        break
            except Exception as e:
                print(f"Error reading {html_file}: {e}")
    
    return templates_to_upgrade


def upgrade_template(template_path):
    """تحديث قالب واحد"""
    try:
        content = template_path.read_text(encoding='utf-8')
        original_content = content
        
        # تغيير extends
        for pattern in OLD_EXTENDS_PATTERNS:
            content = re.sub(pattern, NEW_EXTENDS, content)
        
        # إضافة CSS المحسّن إذا لم يكن موجوداً
        if 'form-hero' not in content and 'slideUp' not in content:
            # البحث عن block extra_css أو إضافته
            if '{% block extra_css %}' in content:
                content = content.replace(
                    '{% block extra_css %}',
                    '{% block extra_css %}' + ENHANCED_STYLES
                )
            elif '{% block extra_head %}' in content:
                content = content.replace(
                    '{% block extra_head %}',
                    '{% block extra_head %}' + ENHANCED_STYLES
                )
        
        if content != original_content:
            template_path.write_text(content, encoding='utf-8')
            return True
        return False
        
    except Exception as e:
        print(f"Error upgrading {template_path}: {e}")
        return False


def main():
    print("=" * 60)
    print("تحديث القوالب القديمة إلى القالب المحسّن")
    print("=" * 60)
    
    templates = find_templates_to_upgrade()
    print(f"\nتم العثور على {len(templates)} قالب يحتاج تحديث:\n")
    
    for i, t in enumerate(templates, 1):
        rel_path = t.relative_to(TEMPLATES_DIR)
        print(f"   {i}. {rel_path}")
    
    if not templates:
        print("جميع القوالب محدّثة!")
        return
    
    print(f"\nجاري التحديث...")
    
    upgraded = 0
    failed = 0
    
    for template in templates:
        rel_path = template.relative_to(TEMPLATES_DIR)
        if upgrade_template(template):
            print(f"   OK: {rel_path}")
            upgraded += 1
        else:
            print(f"   SKIP: {rel_path} (لم يتغير)")
            failed += 1
    
    print(f"\n" + "=" * 60)
    print(f"النتائج:")
    print(f"   تم تحديث: {upgraded} قالب")
    print(f"   بدون تغيير: {failed} قالب")
    print("=" * 60)


if __name__ == '__main__':
    main()
