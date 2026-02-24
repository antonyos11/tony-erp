"""Reporting alerts and notifications utilities.

Currently supports logging + optional email and webhook delivery for
high variance costing differences (e.g. FIFO vs Weighted) or other
future anomalies.

Environment / settings (all optional):
  VARIANCE_ALERT_EMAILS          Comma‑separated list of recipient emails.
  VARIANCE_ALERT_WEBHOOK_URL     HTTP POST endpoint for JSON payload.
  VARIANCE_ALERT_MIN_PERCENT     Override default trigger percent (fallback
                                 to per‑request warn_threshold already in views).

If email backend is console it will still output the message there.
Failures in alert dispatch never raise – they are logged and suppressed.
"""
from __future__ import annotations
from typing import Any, Dict
import logging
from django.conf import settings
from django.core.mail import send_mail
from django.utils.timezone import now
from django.db import transaction

try:  # Local import guard to avoid circular issues during early migrations
    from .models import ReportVarianceIncident  # type: ignore
except Exception:  # pragma: no cover - model may not yet exist during migration phase
    ReportVarianceIncident = None  # type: ignore

logger = logging.getLogger('reports.variance')


def _get_recipients() -> list[str]:
    raw = getattr(settings, 'VARIANCE_ALERT_EMAILS', '') or ''
    return [e.strip() for e in raw.split(',') if e.strip()]


def _post_webhook(url: str, payload: Dict[str, Any]):  # pragma: no cover - best effort
    try:
        try:
            import requests  # type: ignore
            requests.post(url, json=payload, timeout=5)
        except Exception:
            # Fallback to urllib (no dependency) if requests not available
            import json, urllib.request
            req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
            urllib.request.urlopen(req, timeout=5)  # noqa: S310
    except Exception as exc:
        logger.warning(f"Variance webhook send failed: {exc}")


def send_variance_alert(report: str, percent: float, threshold: float, date_from, date_to, extra: Dict[str, Any] | None = None):
    """Dispatch a variance alert via logging + optional email / webhook.

    Parameters
    ----------
    report: str           Logical report name (e.g. 'profit_loss')
    percent: float        Absolute variance percent
    threshold: float      Threshold that was used to trigger
    date_from/date_to     Period of report
    extra: dict           Additional contextual metrics
    """
    payload: Dict[str, Any] = {
        'type': 'variance_high',
        'report': report,
        'percent': percent,
        'threshold': threshold,
        'date_from': str(date_from),
        'date_to': str(date_to),
        'timestamp': now().isoformat(),
    }
    if extra:
        payload.update(extra)
    # Always log first
    logger.warning(f"ALERT variance {report} percent={percent} threshold={threshold} range={date_from}->{date_to}")
    # Persist incident (best effort, never raise)
    if ReportVarianceIncident:
        try:
            with transaction.atomic():
                ReportVarianceIncident.objects.create(
                    report=report,
                    percent=percent,
                    threshold_used=threshold,
                    global_min_applied=bool(extra.get('global_min_applied') if extra else False),
                    date_from=date_from,
                    date_to=date_to,
                    extra=extra or None,
                )
        except Exception as exc:  # pragma: no cover - soft failure path
            logger.warning(f"Persist variance incident failed: {exc}")
    # Email
    recipients = _get_recipients()
    if recipients:
        try:
            subject = f"High Variance Alert ({report}) {percent:.2f}%"
            body_lines = [
                f"Report: {report}",
                f"Range: {date_from} -> {date_to}",
                f"Variance: {percent:.2f}% (threshold {threshold:.2f}%)",
            ]
            if extra:
                for k, v in extra.items():
                    body_lines.append(f"{k}: {v}")
            body = '\n'.join(body_lines)
            send_mail(subject, body, getattr(settings, 'EMAIL_FROM', 'no-reply@example.com'), recipients, fail_silently=True)
        except Exception as exc:  # pragma: no cover - soft failure
            logger.warning(f"Variance alert email failed: {exc}")
    # Webhook
    url = getattr(settings, 'VARIANCE_ALERT_WEBHOOK_URL', '')
    if url:
        _post_webhook(url, payload)
