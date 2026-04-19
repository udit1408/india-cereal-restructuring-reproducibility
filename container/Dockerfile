FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MPLBACKEND=Agg

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY container/requirements.txt /tmp/revision2-requirements.txt
COPY container/entrypoint.sh /usr/local/bin/revision2-entrypoint

RUN python -m pip install --upgrade pip setuptools wheel && \
    python -m pip install -r /tmp/revision2-requirements.txt && \
    chmod +x /usr/local/bin/revision2-entrypoint

ENTRYPOINT ["/usr/local/bin/revision2-entrypoint"]
