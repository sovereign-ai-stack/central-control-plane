# Sovereign AI Control Plane

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Docker Compose](https://img.shields.io/badge/docker-compose-v2-blue.svg)](https://docs.docker.com/compose/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Security Policy](https://img.shields.io/badge/security-policy-red.svg)](SECURITY.md)
[![Code of Conduct](https://img.shields.io/badge/code%20of-conduct-orange.svg)](CODE_OF_CONDUCT.md)

Sovereign AI Control Plane is an enterprise-grade, self-hosted, air-gapped API gateway, semantic router, and orchestration hub for local LLM ecosystems. Designed for strictly regulated organizations requiring 100% data sovereignty, it unifies distributed, consumer-grade GPU workers into an encrypted mesh, enforces granular multi-tenant quotas, executes sub-5ms intent routing, and provides grounded document retrieval through isolated vector pipelines.

The public repository contains the core orchestration gateway, semantic classification engine, Weaviate RAG integration, LiteLLM proxy configuration, database migrations, and production deployment manifests. It contains no collected organizational data, active API keys, or embedded model weights.

![Platform Overview](./assets/platform.png)

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Core Capabilities](#core-capabilities)
  - [1. Enterprise Security & Multi-Tenancy](#1-enterprise-security--multi-tenancy)
  - [2. Sub-5ms Semantic Routing](#2-sub-5ms-semantic-routing)
  - [3. Isolated Vector RAG Engine](#3-isolated-vector-rag-engine)
  - [4. Microsecond Semantic Caching](#4-microsecond-semantic-caching)
  - [5. Full-Stack Observability & Tracing](#5-full-stack-observability--tracing)
- [Zero-Trust Mesh Networking](#zero-trust-mesh-networking)
- [Requirements](#requirements)
- [Configuration](#configuration)
- [Quick Start](#quick-start)
- [Production Hardening & Reverse Proxy](#production-hardening--reverse-proxy)
- [Backup & Disaster Recovery](#backup--disaster-recovery)
- [Project Structure](#project-structure)
- [Governance](#governance)
- [License](#license)

---

## Architecture Overview

The Central Control Plane orchestrates seven decoupled, resilient modules structured in a zero-trust Hub-and-Spoke pattern:

1. **AI Gateway API (FastAPI):** Central ingress point handling client authentication, dynamic model resolution, rate-limiting, and Server-Sent Events (SSE) streaming.
2. **Semantic Router:** High-speed embedding-based classifier evaluating prompt intent in under 5 milliseconds to prevent unnecessary compute load on heavy models.
3. **Enterprise Web UI (Next.js):** Modern, interactive user workspace featuring live model reasoning (`<think>` CoT inspection), interactive parameter controls, and department shard selection.
4. **LiteLLM Unified Proxy:** Single OpenAI-compatible reverse proxy layer abstracting disparate distributed backend nodes into uniform endpoints with load balancing and fallbacks.
5. **PostgreSQL Relational Ledger:** Persistent storage for user accounts, organizational tenants, quota budgets, audit logs, and document chunk metadata.
6. **Weaviate Vector DB:** Sharded vector engine storing dense embeddings for localized, air-gapped Retrieval-Augmented Generation (RAG).
7. **Central Node Registry:** Continuous discovery and heartbeat monitor tracking distributed GPU workers (`ai-node-agent`) connected over WireGuard.
8. **Langfuse Observability:** Deep tracing suite monitoring step-by-step latency, token budgets, execution costs, and lineage across the entire pipeline.

---

## Core Capabilities

### 1. Enterprise Security & Multi-Tenancy
Compute resources in an on-premise ecosystem are finite and expensive. The Control Plane implements strict tenant boundaries:
- **Hierarchical Governance:** Granular mapping across Organizations -> Teams -> Users.
- **Budget & Quota Controls:** Dedicated token budgets per department, preventing runaway batch jobs or unauthorized resource monopolization.
- **RBAC & API Key Pools:** Scoped API credentials with automated expiration and instant revocation.

![Enterprise Teams and Organizations](./assets/teams-orgs.png)

### 2. Sub-5ms Semantic Routing
Rather than blindly routing every prompt to a massive monolithic model, the Gateway evaluates semantic intent prior to GPU dispatch:
- **Coding Requests:** Dispatched to dedicated code-generation nodes (e.g., `qwen-coder`) with specialized context windows.
- **Deep Reasoning:** Routed to Chain-of-Thought (CoT) reasoning models (e.g., `deepseek-r1`) utilizing `<think>` processing.
- **General Conversation:** Handled by low-latency, lightweight models (e.g., `qwen-2.5-3b-awq`) running on minimal VRAM.
- **Knowledge Queries:** Diverted to the internal RAG ingestion pipeline before LLM generation.

![Coding Intent Routing](./assets/coding-question.png)

### 3. Isolated Vector RAG Engine
Organizations require access to proprietary knowledge without training or fine-tuning models:
- **Departmental Vector Sharding:** Document embeddings are categorized into isolated collections (e.g., HR, Engineering, Legal), ensuring users only retrieve documents within their clearance.
- **Local Embedding Computation:** Embeddings are generated in-process without contacting third-party APIs.
- **Grounded Verification:** Retrieved chunks are injected with exact source metadata to eliminate hallucinations and allow verifiable source citations.

![RAG Knowledge Retrieval](./assets/rag-question.png)

### 4. Microsecond Semantic Caching
Repetitive enterprise questions (e.g., policy queries, common IT helpdesk questions) are intercepted by an in-memory Redis semantic cache. Cached responses are served in sub-millisecond latencies, reducing GPU compute load and electricity consumption to zero for repeat queries.

### 5. Full-Stack Observability & Tracing
Every inference lifecycle is captured and visualized through Langfuse:
- **Token Lineage:** Accurate counts for input prompt tokens, output completion tokens, and reasoning tokens.
- **Step-by-Step Spans:** Latency breakdown across Auth -> Semantic Classification -> Vector Retrieval -> LLM Time-to-First-Token (TTFT).
- **Audit Compliance:** Full traceability required for institutional compliance audits.

![Langfuse Tracing Dashboard](./assets/dashboard.png)

---

## Zero-Trust Mesh Networking

To connect worker nodes located across physical offices, datacenters, or developer workstations without public IP addresses or risky port-forwarding, the cluster relies on **Tailscale / WireGuard**:

1. **Install and authenticate Tailscale on the Central Server:**
   ```bash
   curl -fsSL https://tailscale.com/install.sh | sh
   sudo tailscale up
   ```

2. **Retrieve the immutable Mesh IP address:**
   ```bash
   tailscale ip -4
   # Example output: 100.115.80.12
   ```

3. **Inter-Node Connectivity:**
   Worker nodes (`ai-node-agent`) join the identical Tailscale mesh and register directly with the Central Registry at `http://100.115.80.12:8200`. All internal traffic is point-to-point encrypted using modern ChaCha20-Poly1305 WireGuard protocols.

---

## Requirements

- **Operating System:** Linux (Ubuntu 22.04 LTS / Debian 12 recommended) or Windows Server with WSL2
- **Container Runtime:** Docker Engine 24.0+ and Docker Compose v2.20+
- **Memory (RAM):** Minimum 16 GB (32 GB recommended for large Weaviate vector indexes)
- **Disk Space:** 50 GB SSD storage for database volumes and vector indexes
- **Network:** Tailscale or native WireGuard interface for worker node federation

---

## Configuration

The platform is configured via environment variables. Create a local production configuration file:

```bash
cp .env.example .env
```

Annotated core configuration values:

```dotenv
# ==========================================
# Database Infrastructure (PostgreSQL & Redis)
# ==========================================
POSTGRES_USER=litellm
POSTGRES_PASSWORD=replace_with_strong_production_password
POSTGRES_DB=litellm
DATABASE_URL=postgresql://litellm:replace_with_strong_production_password@postgres:5432/litellm
REDIS_URL=redis://redis:6379/0

# ==========================================
# LiteLLM Proxy Layer
# ==========================================
LITELLM_MASTER_KEY=sk-sovereign-master-production-key
LITELLM_PORT=4000
LITELLM_LOG=WARNING

# ==========================================
# Central Node Registry
# ==========================================
REGISTRY_PORT=8200
NODE_TIMEOUT_SECONDS=60

# ==========================================
# Weaviate Vector Store (RAG)
# ==========================================
RAG_VECTOR_STORE_BACKEND=weaviate
RAG_WEAVIATE_URL=http://weaviate:8080
RAG_WEAVIATE_GRPC_PORT=50051
TRANSFORMERS_OFFLINE=1

# ==========================================
# Langfuse Observability Suite
# ==========================================
LANGFUSE_PUBLIC_KEY=pk-lf-production-public-key
LANGFUSE_SECRET_KEY=sk-lf-production-secret-key
LANGFUSE_HOST=http://langfuse:3000
LANGFUSE_ENABLED=true

# ==========================================
# Gateway & Web UI Ports
# ==========================================
PORT=8000
UI_PORT=8400
```

---

## Quick Start

### 1. Build and Launch the Stack

Start all services in detached mode:

```bash
docker compose up -d --build
```

### 2. Verify Container Health

Ensure all seven core services report a healthy status:

```bash
docker compose ps
```

Expected output:
| Name | Service | Status | Ports |
| --- | --- | --- | --- |
| `enterprise-gateway` | `gateway` | `Up (healthy)` | `0.0.0.0:8000->8000/tcp` |
| `enterprise-ui` | `frontend` | `Up` | `0.0.0.0:8400->8400/tcp` |
| `enterprise-litellm` | `litellm` | `Up (healthy)` | `0.0.0.0:4000->4000/tcp` |
| `enterprise-postgres`| `postgres` | `Up (healthy)` | `127.0.0.1:5432->5432/tcp` |
| `enterprise-redis` | `redis` | `Up (healthy)` | `127.0.0.1:6379->6379/tcp` |
| `enterprise-weaviate`| `weaviate` | `Up (healthy)` | `127.0.0.1:8080->8080/tcp` |
| `enterprise-langfuse`| `langfuse` | `Up` | `0.0.0.0:3000->3000/tcp` |

### 3. Inspect Live Diagnostics

Stream logs for specific subsystems:

```bash
# Monitor incoming inference requests and RAG embeddings
docker compose logs -f gateway

# Monitor GPU node registration and heartbeats
docker compose logs -f registry
```

---

## Production Hardening & Reverse Proxy

For institutional domains with TLS/SSL termination and Server-Sent Events (SSE) streaming support, place Nginx in front of the application:

> [!IMPORTANT]
> `proxy_buffering off;` is strictly mandatory. Enabling buffering disrupts real-time token streaming, causing responses to buffer until generation terminates.

```nginx
server {
    listen 80;
    server_name ai.yourdomain.internal;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ai.yourdomain.internal;

    ssl_certificate /etc/letsencrypt/live/ai.yourdomain.internal/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ai.yourdomain.internal/privkey.pem;

    # 1. Next.js Enterprise Web Interface
    location / {
        proxy_pass http://127.0.0.1:8400;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 2. Real-time Gateway API & SSE Token Streaming
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Critical settings for zero-latency token streaming:
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
        proxy_set_header Connection '';
        chunked_transfer_encoding on;
    }
}
```

---

## Backup & Disaster Recovery

### 1. Relational Ledger & User Audits
Export full PostgreSQL user tables, quotas, and conversational history:

```bash
docker exec -t enterprise-postgres pg_dumpall -c -U litellm > /backups/postgres_$(date +%Y%m%d).sql
```

### 2. Vector Store & Document Embeddings
Include the named Docker volume in routine enterprise snapshot policies:
- Volume: `central-control-plane_weaviate-data`
- Contains: In-process dense vectors, inverted indexes, and document text chunks.

---

## Project Structure

```text
central-control-plane/
├── app/                  # FastAPI gateway core logic, auth routers, and schemas
├── frontend/             # Next.js enterprise UI with CoT streaming and admin panels
├── litellm/              # LiteLLM proxy configuration and fallback pipelines
├── rag/                  # Weaviate vector engine integration and embedding workers
├── registry/             # Node discovery, heartbeat monitor, and health checks
├── semantic/             # Semantic Router models, routes, and threshold logic
├── benchmarks/           # Gateway latency and throughput benchmark scripts
├── tests/                # Automated unit and integration test suite
├── docker-compose.yml    # Complete 7-service orchestration manifest
├── Dockerfile.gateway    # Production multi-stage build for FastAPI gateway
└── server.py             # Entrypoint runner for gateway execution
```

---

## Governance

- Review our [Code of Conduct](CODE_OF_CONDUCT.md) for community participation standards.
- Check the [Contributing Guide](CONTRIBUTING.md) before submitting patches or feature requests.
- Read our [Security Policy](SECURITY.md) for responsible vulnerability disclosure.

---

## License

Distributed under the [MIT License](LICENSE).
