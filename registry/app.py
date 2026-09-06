import json
import logging
import os
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [Registry] %(message)s")
logger = logging.getLogger("Registry")

app = FastAPI(title="Enterprise Node Registry & Dynamic LLM Coordinator", version="2.0.0")

LITELLM_URL = os.environ.get("LITELLM_URL", "http://litellm:4000")
LITELLM_MASTER_KEY = os.environ.get("LITELLM_MASTER_KEY", "sk-lite-1234")
NODE_TIMEOUT_SECONDS = int(os.environ.get("NODE_TIMEOUT_SECONDS", "60"))

# In-memory node store (can be persisted to Redis/Postgres in production)
ACTIVE_NODES: Dict[str, Dict[str, Any]] = {}


class HardwareInfoModel(BaseModel):
    gpus: List[Dict[str, Any]] = []
    total_vram_gb: float = 0.0
    tensor_parallel_size: int = 1
    tier_id: str = "custom"


class NodeRegistrationRequest(BaseModel):
    node_id: str = Field(..., description="Unique node identifier")
    api_base: str = Field(..., description="Reachable HTTP base (e.g. http://10.0.0.5:8000)")
    model_name: str = Field(..., description="Full model identifier (e.g. Qwen/Qwen2.5-7B-Instruct-AWQ)")
    served_model_name: str = Field(..., description="Public alias in gateway (e.g. qwen-7b)")
    supported_roles: List[str] = Field(default_factory=list, description="Virtual role aliases (e.g. general-model, rag-model)")
    hardware: Optional[HardwareInfoModel] = None
    timestamp: float = Field(default_factory=time.time)


class HeartbeatRequest(BaseModel):
    node_id: str
    status: str = "healthy"
    active_requests: int = 0
    timestamp: float = Field(default_factory=time.time)


class DeregisterRequest(BaseModel):
    node_id: str


def call_litellm(method: str, path: str, body: Optional[Dict[str, Any]] = None) -> tuple[int, Dict[str, Any]]:
    """Communicate directly with LiteLLM proxy management API."""
    url = f"{LITELLM_URL.rstrip('/')}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {LITELLM_MASTER_KEY}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8", "replace")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw_err = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw_err)
        except Exception:
            return e.code, {"error": raw_err}
    except Exception as e:
        return 500, {"error": str(e)}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "active_nodes_count": len([n for n in ACTIVE_NODES.values() if n["status"] == "healthy"]),
        "total_registered_nodes": len(ACTIVE_NODES),
    }


def remove_node_from_litellm(node: Dict[str, Any]):
    """Removes all routes and role aliases associated with a dead/unhealthy node from LiteLLM Proxy."""
    models_to_remove = [node.get("served_model_name")] + [r for r in node.get("supported_roles", []) if r != node.get("served_model_name")]
    try:
        # Fetch current models in LiteLLM
        status, resp = call_litellm("GET", "/model/info")
        if status == 200 and "data" in resp:
            for lm in resp["data"]:
                m_info = lm.get("model_info", {})
                if m_info.get("node_id") == node.get("node_id") or lm.get("model_name") in models_to_remove:
                    lid = m_info.get("id")
                    if lid:
                        call_litellm("POST", "/model/delete", {"id": lid})
                        logger.info(f"Purged route '{lm.get('model_name')}' (ID: {lid}) for node '{node.get('node_id')}' from LiteLLM")
    except Exception as e:
        logger.warning(f"Error purging node '{node.get('node_id')}' from LiteLLM: {e}")


@app.post("/nodes/register")
def register_node(req: NodeRegistrationRequest):
    """Registers an AI worker node and injects its model & role aliases into LiteLLM Proxy."""
    clean_base = req.api_base.rstrip("/")
    if not clean_base.endswith("/v1"):
        v1_base = f"{clean_base}/v1"
    else:
        v1_base = clean_base

    # Models and roles to register in LiteLLM
    models_to_register = [req.served_model_name] + [r for r in req.supported_roles if r != req.served_model_name]
    sync_results = {}
    overall_ok = True

    for target_alias in models_to_register:
        litellm_payload = {
            "model_name": target_alias,
            "litellm_params": {
                "model": f"openai/{req.model_name}",
                "api_base": v1_base,
                "api_key": "sk-vllm-dummy",
                "drop_params": True,
            },
            "model_info": {
                "mode": "chat",
                "node_id": req.node_id,
                "physical_model": req.model_name,
            },
        }

        # Register or update in LiteLLM Proxy
        status, body = call_litellm("POST", "/model/new", litellm_payload)
        ok = status in (200, 201, 202)
        
        if not ok and status in (400, 409, 422):
            status, body = call_litellm("POST", "/model/update", litellm_payload)
            ok = status in (200, 201)

        sync_results[target_alias] = {"status": status, "success": ok}
        if not ok:
            overall_ok = False

    node_record = {
        "node_id": req.node_id,
        "api_base": req.api_base,
        "model_name": req.model_name,
        "served_model_name": req.served_model_name,
        "supported_roles": req.supported_roles,
        "hardware": req.hardware.model_dump() if req.hardware else {},
        "status": "healthy" if overall_ok else "litellm_error",
        "registered_at": time.time(),
        "last_heartbeat": time.time(),
        "litellm_sync_status": sync_results,
    }
    ACTIVE_NODES[req.node_id] = node_record

    logger.info(f"Node '{req.node_id}' registered successfully (Model: {req.served_model_name}, Roles: {req.supported_roles}). Sync: {overall_ok}")
    return {
        "success": overall_ok,
        "node_id": req.node_id,
        "served_model_name": req.served_model_name,
        "supported_roles": req.supported_roles,
        "litellm_sync": sync_results,
    }


@app.post("/nodes/heartbeat")
def record_heartbeat(req: HeartbeatRequest):
    """Processes node heartbeat ping and handles auto-disable on error/unavailable."""
    if req.node_id not in ACTIVE_NODES:
        raise HTTPException(status_code=404, detail="Node is not registered. Please call /nodes/register first.")
    
    node = ACTIVE_NODES[req.node_id]
    prev_status = node.get("status")
    node["last_heartbeat"] = time.time()
    node["status"] = req.status
    node["active_requests"] = req.active_requests

    # If node transitioned from healthy to unhealthy/unavailable, automatically remove from LiteLLM
    if req.status != "healthy" and prev_status == "healthy":
        logger.warning(f"⚠️ Node '{req.node_id}' reported status '{req.status}'. Automatically disabling its LiteLLM routes...")
        remove_node_from_litellm(node)
    
    return {"status": "acknowledged", "node_id": req.node_id, "current_status": req.status}


@app.post("/nodes/deregister")
def deregister_node(req: DeregisterRequest):
    """Deregisters a node and automatically removes it from LiteLLM Proxy."""
    if req.node_id in ACTIVE_NODES:
        node = ACTIVE_NODES.pop(req.node_id)
        remove_node_from_litellm(node)
        logger.info(f"Node '{req.node_id}' manually deregistered and purged from LiteLLM.")
        return {"success": True, "node_id": req.node_id}
    return {"success": False, "message": "Node not found"}


@app.get("/nodes")
def list_nodes():
    """Returns status of all nodes, marking stale ones as offline and purging dead routes."""
    now = time.time()
    results = []
    for node_id, data in list(ACTIVE_NODES.items()):
        elapsed = now - data["last_heartbeat"]
        node_copy = dict(data)
        node_copy["seconds_since_last_heartbeat"] = round(elapsed, 1)
        if elapsed > NODE_TIMEOUT_SECONDS and data.get("status") == "healthy":
            data["status"] = "offline"
            node_copy["status"] = "offline"
            logger.warning(f"⏰ Node '{node_id}' timed out after {round(elapsed, 1)}s. Auto-purging from LiteLLM...")
            remove_node_from_litellm(data)
        results.append(node_copy)
    return results


@app.get("/models")
def list_gateway_models():
    """Fetches currently live models from LiteLLM Proxy."""
    status, body = call_litellm("GET", "/v1/models")
    return body if status == 200 else {"error": "LiteLLM unreachable", "models": [n["served_model_name"] for n in ACTIVE_NODES.values()]}