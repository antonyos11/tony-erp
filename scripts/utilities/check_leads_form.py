import os
import django
import sys

# Setup Django environment
sys.path.append('/var/www/tony_erp')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from hr.forms import LeaveRequestForm

def check_form():
    try:
        form = LeaveRequestForm()
        print(f"Form class: {form.__class__.__name__}")
        print(f"Fields count: {len(form.fields)}")
        for name, field in form.fields.items():
            print(f"- {name}: {field.__class__.__name__}")
            
        # Verify rendered output snippet
        print("\nRender snippet:")
        print(str(form)[:200] + "...")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    check_form()
