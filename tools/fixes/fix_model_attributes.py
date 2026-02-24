#!/usr/bin/env python
"""
Script to add missing ID fields and fix Django model relationships
"""

import os
import re
from pathlib import Path


def fix_model_attributes(file_path):
    """Fix missing model attributes in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Add ID fields to models that don't have them explicitly
        # Pattern to find class definitions that are Django models
        model_pattern = r'class\s+(\w+)\(models\.Model\):\s*\n((?:\s+""".*?"""\s*\n)?)((?:\s+[A-Z_]+\s*=.*?\n)*)'
        
        def add_id_field(match):
            class_name = match.group(1)
            docstring = match.group(2) or ''
            constants = match.group(3) or ''
            
            # Check if ID field already exists
            if 'id = models.AutoField' in match.group(0):
                return match.group(0)  # Already has explicit ID
                
            # Add explicit ID field
            return f'class {class_name}(models.Model):\n{docstring}{constants}    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking\n'
        
        # Apply the transformation
        content = re.sub(model_pattern, add_id_field, content, flags=re.MULTILINE | re.DOTALL)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed models in: {file_path}")
            return True
        else:
            return False
            
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main():
    """Main function to process all model files."""
    base_dir = Path(__file__).parent
    model_files = list(base_dir.rglob('*models.py'))
    
    fixed_count = 0
    for model_file in model_files:
        # Skip this script itself
        if model_file.name == 'fix_model_attributes.py':
            continue
            
        if fix_model_attributes(model_file):
            fixed_count += 1
    
    print(f"\nFixed {fixed_count} model files total.")


if __name__ == '__main__':
    main()