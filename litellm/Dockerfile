# syntax=docker/dockerfile:1

FROM python:3.11-slim-bookworm

WORKDIR /app

# ============================================================
# Debian packages - Iranian Arvan mirror
# ============================================================

RUN rm -f /etc/apt/sources.list.d/debian.sources \
    && printf '%s\n' \
        'deb [trusted=yes] http://mirror.arvancloud.ir/debian bookworm main' \
        'deb [trusted=yes] http://mirror.arvancloud.ir/debian bookworm-updates main' \
        > /etc/apt/sources.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        gcc \
        libpq-dev \
        git \
        nodejs \
        npm \
    && rm -rf /var/lib/apt/lists/*

# ============================================================
# Prisma CLI
# ============================================================

RUN npm install -g prisma@5.17.0

# ============================================================
# Python packages - Iranian Liara PyPI mirror
# ============================================================

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install \
        --index-url https://package-mirror.liara.ir/repository/pypi/simple \
        --trusted-host package-mirror.liara.ir \
        "litellm[proxy]" \
        prisma \
        psycopg2-binary \
        redis \
        "langfuse>=2.50.0,<3.0.0"

# ============================================================
# Generate Prisma client
# ============================================================

RUN python -c "import litellm, os; p=os.path.join(os.path.dirname(litellm.__file__), 'proxy', 'schema.prisma'); os.system(f'prisma generate --schema {p}')"

EXPOSE 4000

ENTRYPOINT ["litellm"]