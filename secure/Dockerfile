# =============================================================================
#  DevSecOps Workshop - Dockerfile REMEDIADO (versión segura)
# =============================================================================
#  Cambios respecto al Dockerfile vulnerable:
#
#   [1] Imagen base actualizada y "slim" / distroless-friendly
#   [2] Sin secretos hardcodeados — los secretos vienen de SecretsManager
#   [3] Sin password de root, sin usuario backdoor
#   [4] Sin SSH server instalado
#   [5] Usuario no privilegiado (USER appuser)
#   [6] Solo puerto 8080 expuesto
#   [7] Multi-stage build para reducir superficie de ataque
#   [8] HEALTHCHECK para observabilidad
# =============================================================================

# ---------- Stage 1: build ----------
FROM python:3.12-alpine AS builder

WORKDIR /build
COPY app/requirements.txt .
RUN pip install --no-cache-dir --user --upgrade pip \
    && pip install --no-cache-dir --user -r requirements.txt

# ---------- Stage 2: runtime ----------
FROM python:3.12-alpine

LABEL maintainer="devsecops-workshop"
LABEL description="Secure container for DevSecOps demo"

# Crear usuario no privilegiado
RUN addgroup -S appgroup && adduser -S appuser -G appgroup -h /app

WORKDIR /app

# Copiar dependencias del stage builder
COPY --from=builder /root/.local /home/appuser/.local
COPY --chown=appuser:appgroup app/ .

# PATH para los binarios instalados con --user
ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_VERSION=1.0.0

# Cambiar a usuario no privilegiado (USER directive)
USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -q --spider http://localhost:8080/health || exit 1

# Usar gunicorn (servidor de producción) en lugar del dev server de Flask
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "app:app"]
