"""
Monitoring & Error Tracking Configuration
"""
import os
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.redis import RedisIntegration


def setup_sentry():
    dsn = os.getenv('SENTRY_DSN', '')
    if dsn:
        sentry_sdk.init(
            dsn=dsn,
            integrations=[
                DjangoIntegration(),
                CeleryIntegration(),
                RedisIntegration(),
            ],
            traces_sample_rate=0.1,
            send_default_pii=False,
            environment=os.getenv('SENTRY_ENVIRONMENT', 'production'),
        )
        print("Sentry monitoring enabled")
    else:
        print("Sentry DSN not configured - monitoring disabled")
