# Internationalization (i18n) Workflow

This project supports Arabic (default) and English.

## Directory Structure
```
locale/
  ar/LC_MESSAGES/django.po
  en/LC_MESSAGES/django.po
```

## Adding / Updating Strings
1. Wrap strings in templates with `{% trans "..." %}` or `{% blocktrans %}` for multi-line / variables.
2. In Python code use `from django.utils.translation import gettext as _` then `_("Text")`.

## Extract Messages
Automatic extraction requires GNU gettext (`xgettext`, `msgmerge`, etc.). On Windows install via one of:
- MSYS2: install base msys2, then `pacman -S mingw-w64-x86_64-gettext` and add to PATH.
- Scoop: `scoop install gettext`.
- Chocolatey: `choco install gettext`.

Verify: `xgettext --version` should work in the same shell that runs Django.

Then run (from project root):
```
python manage.py makemessages -l ar -l en -i venv -i .venv -i staticfiles
```
Add `-v 2` for verbose.

## Translate
Open each `django.po` and fill `msgstr` values (Arabic file uses original Arabic text already; English file contains translations).

## Compile
```
python manage.py compilemessages
```
Generates `.mo` files under each `LC_MESSAGES` directory.

## Testing Language Switching
In `settings.py` confirm:
```
USE_I18N = True
LANGUAGE_CODE = 'ar'
LANGUAGES = [ ('ar','Arabic'), ('en','English') ]
LOCALE_PATHS = [ BASE_DIR / 'locale' ]
MIDDLEWARE` includes `LocaleMiddleware` after `SessionMiddleware` and before `CommonMiddleware`.
```
Switch language for a request by:
- Adding `?lang=en` if `LocaleMiddleware` + custom URL param logic implemented, or
- Setting `django_language` session key, or
- Sending `Accept-Language: en` header, or
- Temporarily set `LANGUAGE_CODE = 'en'` and restart server.

## Adding New Language
1. Add to `LANGUAGES` in settings.
2. Run `makemessages -l <code>`.
3. Translate and `compilemessages`.

## CI Suggestion
Add a CI step that runs `makemessages` and fails if `git diff --quiet locale` reports changes (ensuring catalogs updated in commits).

## Common Issues
| Symptom | Cause | Fix |
|---------|-------|-----|
| `makemessages` creates no files | Missing gettext binaries | Install gettext and ensure in PATH |
| Non-Arabic text still Arabic | Templates not tagged | Add `{% load i18n %}` and wrap strings |
| Python strings not translated | Not wrapped with `_()` | Import `_` and wrap |
| `UnicodeDecodeError` compiling | Wrong file encoding | Ensure `.po` saved as UTF-8 |

## Next Steps (Backlog)
- Tag remaining templates (reports, inventory, sales export pages).
- Wrap model `verbose_name` / `verbose_name_plural`.
- Translate flash messages & DRF serializer / validator texts.
- Provide language switcher UI element.
