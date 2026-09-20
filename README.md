<div align="center">
  <h1>🛡️ Sovereign AI: Central Control Plane</h1>
  <p><strong>The Intelligence Gateway & Orchestrator for the Sovereign AI Ecosystem</strong></p>
</div>

---

## 🎬 Architecture Demo
Watch the Sovereign AI system in action, showcasing how the Control Plane orchestrates Semantic Routing and RAG instantly:

<video src="./assets/demo.mp4" width="100%" controls></video>

*(If the video does not load automatically, you can download it from the ssets folder).*

## 🚀 Overview
The **Central Control Plane** serves as the master API Gateway, Authentication Provider, and Semantic Router for the completely offline, air-gapped Sovereign AI infrastructure. 

It intercepts user requests, manages enterprise quotas (via PostgreSQL), securely caches repeating queries (via Redis), dynamically injects organizational knowledge (via Weaviate), and routes prompts to the optimal decentralized GPU node (AI Node Agents) within a zero-trust Mesh Network.

## 🧠 Core Components
1. **Semantic Router (< 5ms Latency):** 
   - Dynamically analyzes incoming requests to classify their intent (General, Coding, Reasoning, RAG, Cache).
   - Routes requests directly to the cheapest or most specialized backend without wasting compute.
2. **LiteLLM Proxy:** 
   - Translates and unifies all distributed model endpoints into a single, OpenAI-compatible API interface.
3. **Vector Knowledge Base (Weaviate):** 
   - Intercepts requests meant for internal documentation and shards out RAG (Retrieval-Augmented Generation) context before forwarding it to the language model.
4. **Auth & Ledger (PostgreSQL):** 
   - Strict API key management, rate-limiting, and enterprise quota enforcement.
5. **Observability (Langfuse):** 
   - Fully traces token consumption, network paths, and step-by-step logic latency.

## 🛠️ Tech Stack
- **Framework:** FastAPI, Python
- **Proxy:** LiteLLM
- **Databases:** PostgreSQL (Relational), Redis (Cache), Weaviate (Vector)
- **Monitoring:** Langfuse
- **Infrastructure:** Docker Compose, Tailscale/WireGuard (for secure Mesh Node connection)

## 📂 Repository Integration
This repository works in tandem with the i-node-agent repository, which acts as the execution backend (vLLM/Ray) for the requests brokered by this Control Plane.
