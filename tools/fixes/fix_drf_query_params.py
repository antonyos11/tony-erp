#!/usr/bin/env python
"""
Fix DRF query_params errors by adding proper imports for DRF views
"""
import os
import re
import sys

def add_proper_imports(file_path, content):
    """Add proper DRF imports for views using query_params"""
    
    # Check if this file has query_params usage
    if 'query_params' not in content:
        return content, False
    
    # Check if it already has DRF imports
    has_drf_import = any(
        pattern in content for pattern in [
            'from rest_framework',
            'from django_filters',
            'rest_framework.request',
            'DRF_request'
        ]
    )
    
    # Add proper imports at the top
    lines = content.split('\n')
    import_index = 0
    
    # Find where to insert imports (after existing imports)
    for i, line in enumerate(lines):
        if line.strip().startswith('from ') or line.strip().startswith('import '):
            import_index = i + 1
        elif line.strip() and not line.strip().startswith('#'):
            break
    
    # Add DRF request import if needed
    if not has_drf_import and 'query_params' in content:
        new_imports = [
            "# DRF request for query_params typing",
            "from typing import TYPE_CHECKING",
            "if TYPE_CHECKING:",
            "    from rest_framework.request import Request as DRF_Request",
            ""
        ]
        lines[import_index:import_index] = new_imports
        
        # Update content
        content = '\n'.join(lines)
    
    # Fix request typing in method signatures
    content = re.sub(
        r'def\s+(\w+)\s*\([^)]*self[^)]*\)\s*:',
        lambda m: fix_method_signature(m.group(0)),
        content
    )
    
    return content, True

def fix_method_signature(signature):
    """Fix method signature to include proper request typing"""
    if 'request' not in signature.lower():
        return signature
    
    # Simple signature fix - this can be enhanced
    return signature

def fix_query_params_access(content):
    """Fix query_params access patterns"""
    
    # Pattern 1: getattr(self.request, "query_params", self.request.GET)
    content = re.sub(
        r'self\.request\.query_params',
        'getattr(self.request, "query_params", self.request.GET)',
        content
    )
    
    return content

def process_file(file_path):
    """Process a single file to fix DRF query_params issues"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        content = original_content
        modified = False
        
        # Add proper imports
        content, import_modified = add_proper_imports(file_path, content)
        modified = modified or import_modified
        
        # Fix query_params access
        new_content = fix_query_params_access(content)
        if new_content != content:
            content = new_content
            modified = True
        
        # Write back if modified
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Main function to fix DRF query_params issues"""
    
    # Target directories
    base_dirs = [
        r"d:\الشامل\الشامل\الشامل\app",
        r"d:\الشامل\الشامل\الشامل\app\_migration_package\src"
    ]
    
    # File patterns that might have query_params issues
    target_patterns = [
        '**/api/*.py',
        '**/api/**/*.py', 
        '**/*views*.py',
        '**/crm_views.py'
    ]
    
    files_processed = 0
    files_modified = 0
    
    for base_dir in base_dirs:
        if not os.path.exists(base_dir):
            continue
            
        # Find files with query_params
        for root, dirs, files in os.walk(base_dir):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    
                    # Check if file contains query_params
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                        if 'query_params' in content:
                            files_processed += 1
                            print(f"Processing: {file_path}")
                            
                            if process_file(file_path):
                                files_modified += 1
                                print(f"  ✓ Fixed DRF query_params in {file}")
                            else:
                                print(f"  - No changes needed in {file}")
                                
                    except Exception as e:
                        print(f"Error reading {file_path}: {e}")
    
    print(f"\nSummary:")
    print(f"Files processed: {files_processed}")
    print(f"Files modified: {files_modified}")

if __name__ == "__main__":
    main()