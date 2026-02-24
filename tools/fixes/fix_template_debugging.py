#!/usr/bin/env python
"""
Fix Django template debugging issues in debug_taglibs.py files
"""
import os
import re
import sys

def fix_template_debugging_issues(content):
    """Fix Django template engine access issues"""
    
    modified = False
    
    # Fix 1: Replace get_installed_libraries import with safer version
    if 'from django.template.base import get_installed_libraries' in content:
        content = content.replace(
            'from django.template.base import get_installed_libraries',
            '''# Safe import for template libraries
try:
    from django.template.base import get_installed_libraries
except ImportError:
    # Fallback for different Django versions
    def get_installed_libraries():
        from django.template import engines
        libraries = {}
        for engine in engines.all():
            if hasattr(engine, 'engine') and hasattr(engine.engine, 'template_libraries'):
                libraries.update(getattr(engine.engine, 'template_libraries', {}))
        return libraries'''
        )
        modified = True
    
    # Fix 2: Safe engine.engine access
    if 'hasattr(engine, \'engine\') and hasattr(engine.engine, \'template_libraries\')' in content:
        # Replace unsafe access with safe getattr
        content = re.sub(
            r'libs = getattr\(engine\.engine, "template_libraries", {}\)',
            'libs = getattr(getattr(engine, "engine", None), "template_libraries", {})',
            content
        )
        modified = True
    
    # Fix 3: Add proper type checking for engine access
    if 'if hasattr(engine, \'engine\')' in content:
        content = re.sub(
            r'if hasattr\(engine, \'engine\'\) and hasattr\(engine\.engine, \'template_libraries\'\):',
            '''if (hasattr(engine, 'engine') and 
                getattr(engine, 'engine', None) is not None and 
                hasattr(getattr(engine, 'engine'), 'template_libraries')):''',
            content
        )
        modified = True
    
    # Fix 4: Safe attribute access in loops
    content = re.sub(
        r'libs = getattr\(engine\.engine, "template_libraries", {}\)',
        'engine_obj = getattr(engine, "engine", None)\n            libs = getattr(engine_obj, "template_libraries", {}) if engine_obj else {}',
        content
    )
    if 'engine_obj = getattr' in content:
        modified = True
    
    return content, modified

def fix_sys_stdout_reconfigure(content):
    """Fix sys.stdout.reconfigure issues in settings files"""
    
    modified = False
    
    # Fix reconfigure access with hasattr check
    patterns = [
        (
            r'if hasattr\(sys\.stdout, "reconfigure"\): sys\.stdout\.reconfigure\(encoding="utf-8", errors="replace"\)',
            'if hasattr(sys.stdout, "reconfigure") and callable(getattr(sys.stdout, "reconfigure", None)): sys.stdout.reconfigure(encoding="utf-8", errors="replace")'
        ),
        (
            r'if hasattr\(sys\.stderr, "reconfigure"\): sys\.stderr\.reconfigure\(encoding="utf-8", errors="replace"\)',
            'if hasattr(sys.stderr, "reconfigure") and callable(getattr(sys.stderr, "reconfigure", None)): sys.stderr.reconfigure(encoding="utf-8", errors="replace")'
        )
    ]
    
    for pattern, replacement in patterns:
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
            modified = True
    
    return content, modified

def process_file(file_path):
    """Process a single file to fix template debugging issues"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        content = original_content
        overall_modified = False
        
        # Fix template debugging issues
        if 'debug_taglibs.py' in file_path or 'template' in content.lower():
            content, modified = fix_template_debugging_issues(content)
            overall_modified = overall_modified or modified
        
        # Fix sys.stdout reconfigure issues
        if 'settings.py' in file_path or 'reconfigure' in content:
            content, modified = fix_sys_stdout_reconfigure(content)
            overall_modified = overall_modified or modified
        
        # Write back if modified
        if overall_modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Main function to fix template debugging issues"""
    
    # Target directories
    base_dirs = [
        r"d:\الشامل\الشامل\الشامل\app",
        r"d:\الشامل\الشامل\الشامل\app\_migration_package\src"
    ]
    
    # Target files
    target_files = [
        'debug_taglibs.py',
        'settings.py'
    ]
    
    files_processed = 0
    files_modified = 0
    
    for base_dir in base_dirs:
        if not os.path.exists(base_dir):
            continue
            
        # Find target files
        for root, dirs, files in os.walk(base_dir):
            for file in files:
                if any(target in file for target in target_files):
                    file_path = os.path.join(root, file)
                    files_processed += 1
                    print(f"Processing: {file_path}")
                    
                    if process_file(file_path):
                        files_modified += 1
                        print(f"  ✓ Fixed template debugging issues in {file}")
                    else:
                        print(f"  - No changes needed in {file}")
    
    print(f"\nSummary:")
    print(f"Files processed: {files_processed}")
    print(f"Files modified: {files_modified}")

if __name__ == "__main__":
    main()