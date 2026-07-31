# =============================================================================
# Multi-stage Dockerfile for POS Management System
# =============================================================================
# Stage 1: Base — shared Python setup
# Stage 2: Development — includes dev dependencies
# Stage 3: Production — optimized, minimal image
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Base
# ---------------------------------------------------------------------------
FROM python:3.13-slim AS base

# Prevent Python from writing .pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements/ /app/requirements/

# ---------------------------------------------------------------------------
# Stage 2: Development
# ---------------------------------------------------------------------------
FROM base AS development

# Install development dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements/development.txt

# Copy project source
COPY . /app/

# Create logs directory
RUN mkdir -p /app/logs

# Make entrypoint executable
RUN chmod +x /app/scripts/entrypoint.sh

# Expose port
EXPOSE 8000

# Entrypoint
ENTRYPOINT ["/app/scripts/entrypoint.sh"]

# Default command — Django dev server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# ---------------------------------------------------------------------------
# Stage 3: Production
# ---------------------------------------------------------------------------
FROM base AS production

# Install production dependencies only
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements/production.txt

# Copy project source
COPY . /app/

# Create necessary directories
RUN mkdir -p /app/logs /app/staticfiles /app/media

# Make entrypoint executable
RUN chmod +x /app/scripts/entrypoint.sh

# Create a non-root user for security
RUN addgroup --system appgroup && \
    adduser --system --ingroup appgroup appuser && \
    chown -R appuser:appgroup /app

USER appuser

# Expose port
EXPOSE 8000

# Entrypoint
ENTRYPOINT ["/app/scripts/entrypoint.sh"]

# Default command — Gunicorn
CMD ["gunicorn", "config.wsgi:application", "-c", "/app/docker/gunicorn/gunicorn.conf.py"]
