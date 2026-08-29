FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    libpq-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip --trusted-host pypi.org --trusted-host files.pythonhosted.org --trusted-host pypi.python.org

# Install litellm with proxy extras and redis
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org --trusted-host pypi.python.org "litellm[proxy]" redis

EXPOSE 4000

ENTRYPOINT ["litellm"]
