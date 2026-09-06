# syntax=docker/dockerfile:1
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies + Node.js/npm and pre-package Prisma CLI globally
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    libpq-dev \
    git \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g prisma@5.17.0

# Use BuildKit persistent pip cache to avoid re-downloading PyPI wheels
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org --trusted-host pypi.python.org "litellm[proxy]" prisma psycopg2-binary redis "langfuse>=2.50.0,<3.0.0"

# Generate Prisma Python client bindings using LiteLLM's official schema.prisma
RUN python -c "import litellm, os; p=os.path.join(os.path.dirname(litellm.__file__), 'proxy', 'schema.prisma'); os.system(f'prisma generate --schema {p}')"

EXPOSE 4000

ENTRYPOINT ["litellm"]
