import os, django, traceback
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "accountant_pro.settings")
print("Using settings:", os.environ.get("DJANGO_SETTINGS_MODULE"))
try:
    django.setup()
except Exception as e:
    print("django.setup() failed:", e)
    raise

# Safe template libraries discovery
def get_template_libraries():
    """Safely get installed template libraries"""
    libraries = {}
    
    # Method 1: Skip problematic import
    try:
        pass  # Skip problematic import
    except ImportError:
        pass
    
    # Method 2: Get from template engines  
    try:
        from django.template import engines
        for engine in engines.all():
            if hasattr(engine, 'engine'):
                engine_obj = getattr(engine, 'engine', None)
                if engine_obj and hasattr(engine_obj, 'template_libraries'):
                    engine_libs = getattr(engine_obj, 'template_libraries', {})
                    libraries.update(engine_libs)
        
        print("From template engines - found", len(libraries), "libraries")
        return libraries
    except Exception as e:
        print("Template engines failed:", e)
    
    return libraries

try:
    libs = get_template_libraries()
    print("Total discovered libraries:", len(libs))
    print("Contains billing_extras?", 'billing_extras' in libs)
    if libs:
        print("Some libraries:", sorted(list(libs.keys()))[:10])
    else:
        print("No template libraries found")
        
except Exception as e:
    print("get_installed_libraries not available in this Django version")
    # استخدام طريقة بديلة
    from django.template import engines
    from django.template.backends.django import DjangoTemplates
    
    try:
        engine = engines['django']
        if (hasattr(engine, 'engine') and 
                getattr(engine, 'engine', None) is not None and 
                hasattr(getattr(engine, 'engine'), 'template_libraries')):
            libs = getattr(getattr(engine, "engine", None), "template_libraries", {})
            print("Total discovered libraries (alternative):", len(libs))
            print("Contains billing_extras?", 'billing_extras' in libs)
            print("Some libraries:", sorted(list(libs.keys()))[:40])
        else:
            print("Could not access template libraries through engine")
            libs = {}
    except Exception as e:
        print(f"Alternative library discovery failed: {e}")
        libs = {}

print("Attempting direct import of core.templatetags.billing_extras ...")
try:
    import core.templatetags.billing_extras as be
    print("Imported billing_extras module file:", be.__file__)
    print("Functions:", [n for n in dir(be) if n in ('remaining_amount','paid_percent','tuple_pair')])
except Exception as e:
    print("ERROR importing billing_extras:")
    traceback.print_exc()

# Force refresh: emulate what django does when loading by name
from django.template import Engine
eng = Engine.get_default() if hasattr(Engine, 'get_default') else None
if eng:
    try:
        if hasattr(eng, 'find_library'):
            lib = eng.find_library('billing_extras')  # type: ignore
            print("Engine find_library succeeded, tags available:", list(lib.tags.keys())[:10], 'filters:', list(lib.filters.keys())[:10])
        else:
            print("Engine.find_library method not available")
    except Exception as e:
        print("Engine.find_library failed:", e)
else:
    print("No default Engine available.")

print("Done.")
