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

COPY requirements.txt /tmp/repro-requirements.txt
COPY container/entrypoint.sh /usr/local/bin/repro-entrypoint

RUN python -m pip install --upgrade pip setuptools wheel && \
    python -m pip install -r /tmp/repro-requirements.txt && \
    chmod +x /usr/local/bin/repro-entrypoint

ENTRYPOINT ["/usr/local/bin/repro-entrypoint"]
