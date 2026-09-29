# Multi-stage production container for SUPRA Agentic Taskmaster
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Final runtime image
FROM python:3.12-slim AS runner

WORKDIR /app

# Non-root user for security
RUN groupadd -g 1001 appgroup && \
    useradd -m -d /home/appuser -u 1001 -g appgroup -s /bin/bash appuser

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY src/ ./src/
COPY pyproject.toml README.md ./

ENV PORT=8080 \
    HOME=/home/appuser \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

RUN mkdir -p /app/data/projects && chown -R appuser:appgroup /app

USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

CMD ["uvicorn", "supra_agentic.service:app", "--host", "0.0.0.0", "--port", "8080"]
