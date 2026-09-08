# syntax=docker/dockerfile:1

FROM python:3.12-slim

WORKDIR /app

# Use Iranian Arvan Debian mirror
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

# Install Python dependencies using Liara PyPI mirror
COPY requirements.txt .

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install \
        --index-url https://package-mirror.liara.ir/repository/pypi/simple \
        --trusted-host package-mirror.liara.ir \
        -r requirements.txt

COPY app.py .

EXPOSE 8200

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8200"]