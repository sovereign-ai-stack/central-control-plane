# syntax=docker/dockerfile:1

FROM python:3.12-slim

WORKDIR /app

# ============================================================
# Debian packages - Iranian Arvan mirror
# ============================================================

RUN rm -f /etc/apt/sources.list.d/debian.sources \
    && printf '%s\n' \
        'deb [trusted=yes] http://mirror.arvancloud.ir/debian trixie main' \
        'deb [trusted=yes] http://mirror.arvancloud.ir/debian trixie-updates main' \
        > /etc/apt/sources.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

# ============================================================
# Python dependencies
# ============================================================

COPY requirements.txt .

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install \
        --index-url https://package-mirror.liara.ir/repository/pypi/simple \
        --trusted-host package-mirror.liara.ir \
        -r requirements.txt

# ============================================================
# Application
# ============================================================

COPY config.yaml app.py routes_config.py run_router.sh .

RUN chmod +x run_router.sh

EXPOSE 8300

CMD ["./run_router.sh", "config.yaml"]