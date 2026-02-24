from __future__ import annotations
from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import transaction
import re

TARGET_PATTERNS = [
    re.compile(r"ج.م\s*سعودي", re.IGNORECASE),
    re.compile(r"ج.م", re.IGNORECASE),
]

class Command(BaseCommand):
    help = "فحص الحقول النصية واستبدال كلمة 'ج.م' بالرمز الحالي للنظام (لا يستبدل القيم الرقمية)."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='تشغيل بدون حفظ التغييرات.')
        parser.add_argument('--commit', action='store_true', help='حفظ التغييرات (يتجاهل dry-run).')
        parser.add_argument('--app', help='تحديد تطبيق واحد فقط للفحص.')
        parser.add_argument('--symbol', help='رمز العملة المطلوب وضعه مكان ج.م (افتراضياً من الإعدادات).')

    def handle(self, *args, **opts):
        from django.conf import settings
        symbol = opts.get('symbol') or getattr(settings, 'DEFAULT_CURRENCY_SYMBOL', 'ج.م')
        only_app = opts.get('app')
        dry = opts.get('dry_run') and not opts.get('commit')
        replaced_total = 0
        scanned_models = 0
        from django.db import OperationalError
        for model in apps.get_models():
            if only_app and model._meta.app_label != only_app:
                continue
            concrete_fields = [f for f in model._meta.get_fields() if not (getattr(f, 'auto_created', False) and not getattr(f, 'concrete', False))]
            text_fields = [
                f for f in concrete_fields
                if hasattr(f, 'get_internal_type') and f.get_internal_type() in ('CharField', 'TextField')
            ]
            if not text_fields:
                continue
            scanned_models += 1
            try:
                qs = model.objects.all().only(*[f.name for f in text_fields])
            except Exception as e:
                self.stderr.write(f"تخطي {model.__name__}: خطأ في بناء الاستعلام ({e})")
                continue
            try:
                iterator = qs.iterator(chunk_size=200)
            except OperationalError as e:
                self.stderr.write(f"تخطي {model.__name__}: خطأ قاعدة بيانات ({e})")
                continue
            try:
                for obj in iterator:
                    changed = False
                    original_snapshot = {}
                    for f in text_fields:
                        try:
                            val = getattr(obj, f.name, None)
                        except OperationalError as e:
                            self.stderr.write(f"تخطي حقل {model.__name__}.{f.name} (خطأ قاعدة بيانات: {e})")
                            continue
                        except Exception:
                            continue
                        if not val or not isinstance(val, str):
                            continue
                        new_val = val
                        for pat in TARGET_PATTERNS:
                            new_val = pat.sub(symbol, new_val)
                        if new_val != val:
                            if not changed:
                                original_snapshot['id'] = obj.pk
                            original_snapshot[f.name] = (val, new_val)
                            setattr(obj, f.name, new_val)
                            changed = True
                    if changed:
                        replaced_total += 1
                        if dry:
                            continue
                        try:
                            with transaction.atomic():
                                update_fields = [fname for fname in original_snapshot.keys() if fname != 'id']
                                if update_fields:
                                    obj.save(update_fields=update_fields)
                        except Exception as e:
                            self.stderr.write(f"خطأ حفظ {model.__name__} pk={obj.pk}: {e}")
            except OperationalError as e:
                self.stderr.write(f"تخطي الموديل {model.__name__} أثناء المعالجة (OperationalError: {e})")
            if replaced_total and replaced_total % 100 == 0:
                self.stdout.write(f"... تقدم: {replaced_total} سجل معدل حتى الآن")

        self.stdout.write(self.style.SUCCESS(
            f"تم فحص {scanned_models} موديل. سجلات معدلة: {replaced_total}. وضع: {'محاكاة' if dry else 'حفظ فعلي'}"
        ))
        if dry:
            self.stdout.write("أعد التشغيل مع --commit للحفظ.")
