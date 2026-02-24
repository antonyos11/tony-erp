#!/usr/bin/env python
"""
Script to fix DecimalField default values from integers to Decimal instances
to satisfy type checking requirements.
"""

import os
import re
from pathlib import Path


def fix_decimal_defaults(file_path):
    """Fix DecimalField default values in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Pattern to find DecimalField with integer defaults
        pattern = r'(models\.DecimalField\([^)]*?default=)(\d+)(\)|\s*,)'
        
        def replace_default(match):
            before = match.group(1)
            default_value = match.group(2)
            after = match.group(3)
            return f"{before}Decimal('{default_value}'){after}"
        
        original_content = content
        content = re.sub(pattern, replace_default, content)
        
        # Check if Decimal import exists
        if content != original_content and 'from decimal import Decimal' not in content:
            # Add Decimal import after other imports
            lines = content.split('\n')
            import_insert_pos = 0
            for i, line in enumerate(lines):
                if line.startswith('from ') or line.startswith('import '):
                    import_insert_pos = i + 1
                elif line.strip() and not line.startswith('#'):
                    break
            
            if import_insert_pos == 0:
                # No imports found, add at the beginning
                lines.insert(0, 'from decimal import Decimal')
            else:
                # Check if there's already a decimal import
                has_decimal = any('decimal' in line.lower() for line in lines[:import_insert_pos])
                if not has_decimal:
                    lines.insert(import_insert_pos, 'from decimal import Decimal')
            
            content = '\n'.join(lines)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed: {file_path}")
            return True
        else:
            return False
            
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main():
    """Main function to process all Python files."""
    base_dir = Path(__file__).parent
    python_files = list(base_dir.rglob('*.py'))
    
    fixed_count = 0
    for py_file in python_files:
        # Skip this script itself
        if py_file.name == 'fix_decimal_defaults.py':
            continue
            
        if fix_decimal_defaults(py_file):
            fixed_count += 1
    
    print(f"\nFixed {fixed_count} files total.")


if __name__ == '__main__':
    main()