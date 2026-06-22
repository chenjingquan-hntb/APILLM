# ============================================================
# LLM Relay — Docker 多阶段构建
# ============================================================

# ---- Build Stage: Frontend ----
FROM node:22-alpine AS frontend-builder

WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ .
RUN npm run build

# ---- Runtime Stage: Python ----
FROM python:3.12-alpine AS runtime

WORKDIR /app

# Install system dependencies
RUN apk add --no-cache postgresql-libs

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]" && \
    pip install --no-cache-dir uvicorn[standard]

# Copy application code
COPY app/ app/
COPY alembic.ini .
COPY alembic/ alembic/
COPY scripts/ scripts/

# Copy frontend build from builder stage
COPY --from=frontend-builder /build/frontend/dist/ frontend/dist/

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD python scripts/healthcheck.py --endpoint http://localhost:8000 || exit 1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
