# CRM / ERP System I18N Progress Summary

This document summarizes the internationalization (i18n) status and recent fallback implementation for message compilation.

## Coverage Status
- Templates: Trans/Blocktrans added (initial pass).
- Apps fully localized: exports, users, accounting, inventory, sales, purchases, partners, hr.
- Pending review: Remaining minor apps (if any) for stray literals.

## Catalogs
- Arabic (source msgid) and English (msgstr) maintained under `locale/ar` and `locale/en`.
- All HR-related strings appended.

## Compilation Challenge
System `msgfmt` binary not available -> `.mo` files were not generated previously.

## Fallback Solution
A pure-Python management command `compilemessages_fallback` was added under `core.management.commands`.
Use:
```
python manage.py compilemessages_fallback            # compile all
python manage.py compilemessages_fallback -l ar -l en # specific locales
python manage.py compilemessages_fallback --dry-run  # parse only
```
Generates `django.mo` files so translations become active without GNU gettext.

## Next Steps
1. Run fallback compile and verify language switch at runtime.
2. Optionally install real gettext later for authoritative compilation.
3. Add CI step: run `makemessages --no-location` + diff to detect untranslated additions.
4. Add pluralization QA (Arabic plural forms) and context (`pgettext`) where ambiguous.
5. Smoke test critical model verbose names and choice labels in both locales.

## Notes
- Fallback supports basic plural forms; complex contexts or msgctxt not yet implemented.
- Keep PO headers consistent; ensure `Plural-Forms` present in Arabic catalog.
