"""تهيئة حزمة المشروع.

تم التفاف استيراد Celery للسماح بتشغيل المشروع في بيئة تطوير سريعة بدون تثبيت celery.
"""
try:
	from .celery import app as celery_app  # type: ignore
	__all__ = ('celery_app',)
except Exception:  # pragma: no cover - فشل اختياري
	celery_app = None  # يسمح لـ Django بالاستمرار بدون Celery
	__all__ = ()