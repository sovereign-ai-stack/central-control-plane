# Sovereign AI Control Plane

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Docker Compose](https://img.shields.io/badge/docker-compose-blue.svg)](https://docs.docker.com/compose/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com/)

Sovereign AI Control Plane is a self-hosted, air-gapped API gateway and semantic routing system for enterprise LLM deployments. It securely orchestrates traffic across a decentralized Mesh network of GPU worker nodes, enforces strict quotas, provides sub-5ms semantic routing, and natively integrates Vector RAG using local knowledge bases.

The repository contains the core orchestration layer, proxy configuration, Docker deployment specifications, and migration scripts. It contains no collected organizational data, active API keys, or embedded model weights.

![Architecture Platform](./assets/platform.png)

## Features

- **Semantic Routing:** Sub-5ms intent classification routing requests to specialized handlers (General, Coding, Reasoning, RAG).
- **Unified Proxy Interface:** Provides a single, OpenAI-compatible API across all distributed multi-node models using LiteLLM.
- **Enterprise Authentication:** Strict API key management, rate-limiting, and budget enforcement via PostgreSQL.
- **Microsecond Caching:** Redis-backed semantic caching bypasses GPU overhead entirely for repetitive queries.
- **Grounded Vector RAG:** Intercepts documentation queries, retrieves organizational embeddings from Weaviate, and injects context before model generation.
- **Mesh Network Orchestration:** Securely communicates with headless, distributed \i-node-agent\ instances over Tailscale without public IP exposure.
- **End-to-End Observability:** Full telemetry, latency tracking, and token cost calculation via Langfuse.

## Requirements

- Git
- Docker Engine with Docker Compose v2
- Tailscale (or WireGuard) configured for Mesh node connections
- [ai-node-agent](https://github.com/sovereign-ai-stack/ai-node-agent) running on execution nodes

## Quick start

Clone the repository and spin up the control plane stack:

\\\ash
git clone https://github.com/sovereign-ai-stack/central-control-plane.git
cd central-control-plane

# Copy the sample environment file
cp .env.example .env
\\\

Configure your \.env\ with secure keys:

\\\env
POSTGRES_USER=admin
POSTGRES_PASSWORD=secret_password
LITELLM_MASTER_KEY=sk-sovereign-master
\\\

Start the complete infrastructure using Docker Compose:

\\\ash
docker-compose up -d
\\\

This starts the API Gateway (\:8000\), Semantic Router (\:8300\), LiteLLM Proxy (\:4000\), PostgreSQL, Weaviate, Redis, and Langfuse simultaneously.

## Routing and Observability

The Control Plane dynamically evaluates each prompt without requiring the user to specify a model.

| Route Intent | Assigned Node / Model | Behavior |
| --- | --- | --- |
| \coding\ | Node 2 (\qwen-coder\) | Optimized for complex programming tasks. |
| \easoning\ | Node 3 (\deepseek-r1\) | Utilizes Chain-of-Thought (\<think>\) for logic. |
| \organizational\ | RAG Pipeline (\weaviate\) | Grounds responses in local enterprise data. |
| \general\ | Node 1 (\qwen-7b\) | Fallback for general conversation. |

Every request is traced down to the token level. Access the Langfuse dashboard at \http://localhost:3000\ to inspect the complete lineage:

![Dashboard Tracing](./assets/dashboard.png)

## Node Registration

Once the Control Plane is running, execution nodes (\i-node-agent\) will automatically discover the gateway over the Mesh network and register their hardware capabilities. 

All routing and orchestration remain completely isolated from the public internet.
