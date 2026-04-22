# syntax=docker/dockerfile:1.7
# triage4 container — slim, no external SDKs, dashboard on :8000
#
# Build: docker build -t triage4:0.1.0 .
# Run:   docker run --rm -p 8000:8000 triage4:0.1.0
# Check: curl http://localhost:8000/health
#
# Size target: < 200 MB (pure stdlib + numpy + scipy + fastapi).
# No PHI, no credentials, no ML/robotics SDKs in the base image.

ARG PYTHON_VERSION=3.12

# ---------- builder ----------
FROM python:${PYTHON_VERSION}-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build

# Only what pyproject needs, copied early so layer-caching wins.
COPY pyproject.toml README.md /build/
COPY triage4 /build/triage4
COPY configs /build/configs

RUN pip install --upgrade pip wheel && \
    pip wheel --wheel-dir=/wheels .

# ---------- runtime ----------
FROM python:${PYTHON_VERSION}-slim AS runtime

LABEL org.opencontainers.image.title="triage4" \
      org.opencontainers.image.description="Autonomous stand-off triage stack (decision-support)" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.source="https://github.com/svend4/info150"

# Run as an unprivileged user — triage4 never needs root.
RUN groupadd --system triage && \
    useradd --system --gid triage --home /home/triage --shell /sbin/nologin triage && \
    mkdir -p /home/triage && chown triage:triage /home/triage

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TRIAGE4_CONFIG=/app/configs/production.yaml

WORKDIR /app

COPY --from=builder /wheels /wheels
RUN pip install --no-index --find-links=/wheels triage4 && rm -rf /wheels

COPY configs /app/configs

USER triage

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request, sys; \
sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status == 200 else 1)" \
  || exit 1

CMD ["uvicorn", "triage4.ui.dashboard_api:app", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "1", "--log-level", "info"]
