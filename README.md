<div align="center">
  <h1>🛡️ Sovereign AI: Central Control Plane</h1>
  <p><strong>The Intelligence Gateway, Semantic Router, and Orchestrator for the Sovereign AI Ecosystem</strong></p>
  <img src="./assets/platform.png" width="800" alt="Platform Overview" />
</div>

---

## 🚀 Overview
The **Central Control Plane** serves as the master API Gateway, Authentication Provider, and Semantic Router for the completely offline, air-gapped Sovereign AI infrastructure. 

Instead of connecting directly to large LLMs, users interact exclusively with this highly optimized gateway. It intercepts requests, manages enterprise quotas, securely caches repetitive queries, dynamically injects organizational knowledge (RAG), and routes prompts to the optimal decentralized GPU node (i-node-agent) over a zero-trust Mesh Network.

### 🎬 System Architecture Demo
<video src="./assets/demo.mp4" width="100%" controls></video>

---

## 🧠 Core Architecture & Workflow

### 1. Enterprise Authentication & Quotas (PostgreSQL)
All requests are intercepted to verify organization/team/user identity and enforce strict quota management. GPU compute is expensive; the control plane ensures only authorized queries are routed to inference nodes.
<br><img src="./assets/teams-orgs.png" width="600" alt="Teams and Organizations" />

### 2. Semantic Router (< 5ms Latency)
Before touching any GPU, the Semantic Router evaluates the incoming prompt and determines its intent:
- **General Conversation:** Routed to a lightweight general model (e.g., Qwen-2.5-3B).
- **Coding Tasks:** Routed to a specialized coding node.
- **Deep Reasoning:** Routed to a Chain-of-Thought (CoT) enabled model like DeepSeek-R1.
- **Organization Knowledge (RAG):** Routed through the RAG pipeline.
<br><img src="./assets/coding-question.png" width="600" alt="Coding Question Example" />

### 3. Microsecond Caching (Redis)
If a user asks a question that was recently answered, the Control Plane bypasses the LLM entirely. Redis serves the exact response in microseconds, saving massive compute costs.

### 4. Vector Knowledge Base & RAG (Weaviate)
For queries related to internal documents, the Control Plane integrates with **Weaviate**. It retrieves chunked vector embeddings specific to the user's shard (e.g., HR, Finance) and injects this context into the prompt.
<br><img src="./assets/rag-question.png" width="600" alt="RAG Example" />

### 5. Unified Proxy Interface (LiteLLM)
Instead of forcing developers to manage multiple IP addresses, ports, and model formats, the Control Plane uses **LiteLLM**. It translates all distributed node endpoints into a single, seamless, OpenAI-compatible API interface.

### 6. End-to-End Observability (Langfuse)
Total transparency. Every token generated, the latency of every step (Auth -> Router -> DB -> LLM), and the entire trace of thought (CoT) is logged in **Langfuse**.
<br><img src="./assets/dashboard.png" width="600" alt="Dashboard Overview" />

---

## 🛠️ Technology Stack
- **API & Routing:** FastAPI, Semantic Router
- **Proxy:** LiteLLM
- **Databases:** PostgreSQL (Relational/Auth), Redis (Semantic Cache), Weaviate (Vector Storage)
- **Observability:** Langfuse
- **Networking:** Tailscale / WireGuard (Mesh Network Hub)

---

## 🚀 How to Run the Central Control Plane

### Prerequisites
- Docker & Docker Compose
- A Tailscale/WireGuard network configured (if routing to external AI nodes)

### 1. Environment Setup
Create a .env file in the root directory:
\\\env
POSTGRES_USER=admin
POSTGRES_PASSWORD=secret
LITELLM_MASTER_KEY=sk-sovereign-master
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
\\\

### 2. Launching the Services
Use Docker Compose to spin up the entire Gateway, Proxy, and Database layer:
\\\ash
docker-compose up -d
\\\
This will start:
- gateway (Port 8000)
- semantic-router (Port 8300)
- litellm (Port 4000)
- postgres (Port 5432)
- edis (Port 6379)
- weaviate (Port 8080)
- langfuse (Port 3000)

### 3. Connect Node Agents
Once the Central Control Plane is running, boot up your i-node-agent servers. They will automatically detect their hardware constraints and register themselves to this Control Plane's LiteLLM proxy securely over the mesh network.

---
*Developed as the command center for the Sovereign AI decentralized ecosystem.*
