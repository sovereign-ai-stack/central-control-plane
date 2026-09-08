# syntax=docker/dockerfile:1

FROM node:20-slim AS prisma

RUN npm install -g prisma@5.17.0


FROM python:3.11-slim AS builder

WORKDIR /app

# Debian packages
RUN rm -f /etc/apt/sources.list.d/debian.sources \
    && printf '%s\n' \
        'deb [trusted=yes] http://archive.debian.petiak.ir/debian trixie main' \
        'deb [trusted=yes] http://archive.debian.petiak.ir/debian trixie-updates main' \
        > /etc/apt/sources.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        gcc \
        git \
    && rm -rf /var/lib/apt/lists/*

# Copy Prisma CLI from Node stage
COPY --from=prisma /usr/local/lib/node_modules /usr/local/lib/node_modules
COPY --from=prisma /usr/local/bin/prisma /usr/local/bin/prisma

# Python dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip \
    && pip install \
        --index-url https://package-mirror.liara.ir/repository/pypi/simple \
        --trusted-host package-mirror.liara.ir \
        "litellm[proxy]" \
        prisma \
        psycopg2-binary \
        redis \
        "langfuse>=2.50.0,<3.0.0"

# Generate Prisma client
RUN python -c "import litellm, os; p=os.path.join(os.path.dirname(litellm.__file__), 'proxy', 'schema.prisma'); os.system(f'prisma generate --schema {p}')"

EXPOSE 4000

ENTRYPOINT ["litellm"]