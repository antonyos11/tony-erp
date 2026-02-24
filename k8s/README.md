# Tony ERP - Kubernetes Deployment Guide

## نظرة عامة

هذا الدليل يشرح كيفية نشر نظام Tony ERP على Kubernetes.

## المتطلبات

- Kubernetes cluster (v1.20+)
- kubectl configured
- Docker registry (Docker Hub, AWS ECR, etc.)
- PersistentVolume support (for PostgreSQL, Redis, media files)

## البنية

```
k8s/
├── namespace.yaml          # Namespace للنظام
├── configmap.yaml          # إعدادات التطبيق
├── secrets.yaml            # المفاتيح والأسرار
├── postgres.yaml           # PostgreSQL database
├── redis.yaml              # Redis cache
├── django-deployment.yaml  # Django application
├── celery-worker.yaml      # Celery workers
├── celery-beat.yaml        # Celery scheduler
├── nginx.yaml              # Nginx reverse proxy
├── services.yaml           # Kubernetes services
├── ingress.yaml            # Ingress للوصول الخارجي
└── volumes.yaml            # PersistentVolumeClaims

