# ============================================================
# Tony ERP - Multi-stage Production Dockerfile
# ============================================================

# Stage 1: Builder - compile dependencies
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies into /install prefix
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Runtime - slim production image
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=accountant_pro.settings

WORKDIR /app

# Install runtime dependencies only (no compilers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    default-libmysqlclient-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy compiled Python packages from builder
COPY --from=builder /install /usr/local

# Copy project code
COPY . /app/

# Create required directories
RUN mkdir -p logs media staticfiles backups

# Create non-root user for security
RUN adduser --disabled-password --gecos '' appuser \
    && chown -R appuser:appuser /app
USER appuser

# Collect static files - show warnings instead of silently failing
RUN python manage.py collectstatic --noinput --settings=accountant_pro.settings 2>&1 || \
    echo "WARNING: collectstatic failed - static files may be missing"

# Health check using Python instead of curl to reduce dependencies
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/live/')" || exit 1

# Expose port
EXPOSE 8000

# Default command (gunicorn for production)
CMD ["gunicorn", "accountant_pro.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--threads", "2", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]