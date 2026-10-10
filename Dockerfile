# ---- build stage ---------------------------------------------------------
FROM python:3.11-slim AS base

# System dependencies.
# To enable real Tesseract OCR later, uncomment the next line and rebuild:
#   RUN apt-get update && apt-get install -y tesseract-ocr && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get install -y --no-install-recommends \
        libglib2.0-0 \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd --gid 1001 appgroup \
 && useradd  --uid 1001 --gid 1001 --no-create-home appuser

WORKDIR /app

# Install Python dependencies (core only)
COPY requirements/ requirements/
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements/base.txt

# Copy application source
COPY src/ ./src/

# PYTHONPATH so "from docint..." imports work
ENV PYTHONPATH=/app/src

# Upload directory (overridable via docker-compose env)
ENV UPLOAD_DIR=/data/uploads

# Run as non-root
USER appuser

EXPOSE 8000

CMD ["uvicorn", "docint.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
