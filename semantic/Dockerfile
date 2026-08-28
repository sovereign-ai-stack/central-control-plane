FROM python:3.12-slim

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install requirements with trusted hosts to avoid proxy/hash mismatch issues
RUN pip install --upgrade pip --trusted-host pypi.org --trusted-host files.pythonhosted.org --trusted-host pypi.python.org

COPY requirements.txt .
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org --trusted-host pypi.python.org -r requirements.txt

COPY config.yaml app.py routes_config.py run_router.sh .
RUN chmod +x run_router.sh

EXPOSE 8300

CMD ["./run_router.sh", "config.yaml"]