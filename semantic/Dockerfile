# syntax=docker/dockerfile:1
FROM python:3.12-slim

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for Docker layer caching
COPY requirements.txt .

# Use BuildKit persistent pip cache to prevent re-downloading wheels (torch, sentence-transformers, etc.)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org --trusted-host pypi.python.org -r requirements.txt

COPY config.yaml app.py routes_config.py run_router.sh .
RUN chmod +x run_router.sh

EXPOSE 8300

CMD ["./run_router.sh", "config.yaml"]