import os
import re

# Set the directory
directory = '/var/www/tony_erp/templates/ecommerce'

# Regex patterns for finding white backgrounds
patterns = [
    (r'background:\s*#fff(fff)?\b', 'background: rgba(15, 23, 42, 0.6) !important; backdrop-filter: blur(10px);'),
    (r'background:\s*white\b', 'background: rgba(15, 23, 42, 0.6) !important; backdrop-filter: blur(10px);'),
    (r'bg-white', 'bg-dark-glass'),  # We will assume bg-dark-glass will be styled or we replace class directly
]

# Walk through the directory
for root, dirs, files in os.walk(directory):
    for file in files:
        if file.endswith('.html'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r') as f:
                content = f.read()
            
            new_content = content
            
            # Replace inline styles and CSS
            new_content = re.sub(r'background:\s*#fff(fff)?\s*;', 'background: rgba(15, 23, 42, 0.6) !important; backdrop-filter: blur(10px); color: white;', new_content, flags=re.IGNORECASE)
            new_content = re.sub(r'background:\s*white\s*;', 'background: rgba(15, 23, 42, 0.6) !important; backdrop-filter: blur(10px); color: white;', new_content, flags=re.IGNORECASE)
            new_content = re.sub(r'background:\s*linear-gradient\([^)]*#fff[^)]*\);', 'background: rgba(15, 23, 42, 0.6) !important; backdrop-filter: blur(10px);', new_content, flags=re.IGNORECASE)
            
            # Replace bootstrap classes
            new_content = new_content.replace('bg-white', 'bg-dark bg-opacity-75')
            new_content = new_content.replace('bg-light', 'bg-dark bg-opacity-50')
            
            if new_content != content:
                print(f"Updating {filepath}")
                with open(filepath, 'w') as f:
                    f.write(new_content)

print("Batch update complete.")
