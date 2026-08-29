FROM python:3.11-slim

WORKDIR /app

# Install system dependencies + Node.js/npm so Prisma generate works 100% offline
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    libpq-dev \
    git \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip --trusted-host pypi.org --trusted-host files.pythonhosted.org --trusted-host pypi.python.org

# Install litellm with proxy extras, prisma ORM for PostgreSQL DB support, and redis
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org --trusted-host pypi.python.org "litellm[proxy]" prisma psycopg2-binary redis

# Generate Prisma Python client bindings using LiteLLM's official schema.prisma
RUN python -c "import litellm, os; p=os.path.join(os.path.dirname(litellm.__file__), 'proxy', 'schema.prisma'); os.system(f'prisma generate --schema {p}')"

EXPOSE 4000

ENTRYPOINT ["litellm"]
