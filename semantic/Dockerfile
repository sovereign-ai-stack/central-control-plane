FROM python:3.12-slim

WORKDIR /app

# Install system dependencies if required for C-extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.yaml app.py routes_config.py run_router.sh .
RUN chmod +x run_router.sh

EXPOSE 8300

CMD ["./run_router.sh", "config.yaml"]