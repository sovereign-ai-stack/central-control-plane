"""
Managed Model & Node Orchestration Service.
Handles dynamic addition, role binding, enable/disable toggling,
and lifecycle synchronization between Database, LiteLLM Proxy, and Node Registry.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.integrations.litellm import litellm_client
from app.integrations.registry import registry_client
from app.models.managed_model import ManagedModelModel


class ManagedModelService:
    @staticmethod
    def _format_litellm_model_string(provider: str, model_id: str) -> str:
        prov = (provider or "openai").lower().strip()
        mid = (model_id or "").strip()

        if "/" in mid:
            return mid
        return f"{prov}/{mid}"

    @classmethod
    def sync_model_to_litellm(cls, model_obj: ManagedModelModel) -> bool:
        """Registers or updates a managed model in LiteLLM Proxy under its assigned role."""
        if not model_obj.is_enabled:
            # If disabled, remove virtual alias from LiteLLM
            litellm_client.delete_model_from_proxy(model_name=model_obj.assigned_role)
            return True

        litellm_model = cls._format_litellm_model_string(model_obj.provider, model_obj.model_id)
        api_base = model_obj.api_base if model_obj.api_base else None

        model_info = {
            "mode": "chat",
            "db_model_id": model_obj.id,
            "provider": model_obj.provider,
            "physical_model": model_obj.model_id,
            "context_window": model_obj.context_window,
        }

        # Register under assigned role (e.g. general-model, coding-model, reasoning-model, rag-model)
        role_ok = litellm_client.register_model(
            model_name=model_obj.assigned_role,
            litellm_model=litellm_model,
            api_key=model_obj.api_key or None,
            api_base=api_base,
            model_info=model_info,
        )

        return role_ok

    @classmethod
    def _sync_node_to_litellm(cls, node: Dict[str, Any]) -> bool:
        """Registers all roles and aliases of an active GPU node into LiteLLM Proxy."""
        node_id = node.get("node_id")
        if not node_id:
            return False
        api_base = node.get("api_base", "").rstrip("/")
        if not api_base:
            return False
        v1_base = api_base if api_base.endswith("/v1") else f"{api_base}/v1"

        served_model = node.get("served_model_name") or "coding-model"
        physical_model = node.get("model_name") or served_model

        aliases = [served_model]
        if physical_model not in aliases:
            aliases.append(physical_model)
        for r in node.get("supported_roles", []):
            if r not in aliases:
                aliases.append(r)
        # Always guarantee general-model is registered as an alias so general queries work
        if "general-model" not in aliases:
            aliases.append("general-model")

        all_ok = True
        for target_alias in aliases:
            model_info = {
                "id": f"{node_id}-{target_alias.replace('/', '_').replace(':', '_')}",
                "mode": "chat",
                "node_id": node_id,
                "provider": "local_node",
                "physical_model": physical_model,
                "description": f"GPU Node: {node_id} | Model: {physical_model}",
            }
            ok = litellm_client.register_model(
                model_name=target_alias,
                litellm_model=f"openai/{served_model}",
                api_key="sk-vllm-dummy",
                api_base=v1_base,
                model_info=model_info,
            )
            if not ok:
                all_ok = False
        return all_ok

    @classmethod
    def reconcile_all_models_with_litellm(cls, db: Session) -> Dict[str, Any]:
        """
        Full synchronization between Database, Registry Nodes, and LiteLLM Proxy:
        1. Purges all orphaned, static dummy, or phantom models from LiteLLM.
        2. Registers all active DB models into LiteLLM Proxy under their respective system roles.
        3. Ensures active hardware GPU nodes are synchronized into LiteLLM.
        4. Guarantees all standard system roles have a working backend.
        """
        try:
            db_models = db.query(ManagedModelModel).all()
            enabled_models = [m for m in db_models if m.is_enabled and m.provider != "local_node"]
            enabled_map = {m.id: m for m in enabled_models}

            # 1. Fetch current models from LiteLLM Proxy and Registry Nodes
            litellm_models = litellm_client.get_registered_models()
            active_nodes = registry_client.get_nodes()
            healthy_nodes = [n for n in active_nodes if n.get("status") == "healthy"]
            deleted_count = 0

            # 2. Purge stale/orphaned DB models from LiteLLM (preserve active nodes)
            active_node_ids = {n.get("node_id") for n in healthy_nodes}
            for lm in litellm_models:
                m_info = lm.get("model_info", {})
                lid = m_info.get("id")
                db_mid = m_info.get("db_model_id")
                node_id = m_info.get("node_id")

                # If it's an active GPU node, verify the node is still alive
                if node_id:
                    if node_id not in active_node_ids and lid:
                        litellm_client.delete_model_by_id(lid)
                        deleted_count += 1
                    continue

                # If this model was managed by DB, check if it's still enabled and role matches
                if db_mid:
                    if db_mid not in enabled_map or lm.get("model_name") != enabled_map[db_mid].assigned_role:
                        if lid:
                            litellm_client.delete_model_by_id(lid)
                            deleted_count += 1
                elif enabled_models:
                    if lid:
                        litellm_client.delete_model_by_id(lid)
                        deleted_count += 1

            # 3. Register/Update all enabled DB models into LiteLLM
            synced_count = 0
            for m in enabled_models:
                cls.sync_model_to_litellm(m)
                synced_count += 1

            # 4. Sync all healthy GPU worker nodes into LiteLLM (respecting manual disable)
            disabled_node_ids = {
                m.id.replace("node_", "", 1)
                for m in db_models
                if m.provider == "local_node" and not m.is_enabled
            }
            allowed_nodes = [n for n in healthy_nodes if n.get("node_id") not in disabled_node_ids]

            for node in allowed_nodes:
                cls._sync_node_to_litellm(node)
                synced_count += 1

            # 5. Guarantee all standard roles have a working backend dynamically
            standard_roles = ["general-model", "coding-model", "reasoning-model", "rag-model"]
            fresh_litellm_models = litellm_client.get_registered_models()
            active_roles = {lm.get("model_name") for lm in fresh_litellm_models if lm.get("model_name")}

            # Choose fallback source: First prefer enabled DB model, then allowed GPU node
            if enabled_models:
                fallback_source = enabled_models[0]
                for r in standard_roles:
                    if r not in active_roles:
                        litellm_model = cls._format_litellm_model_string(fallback_source.provider, fallback_source.model_id)
                        litellm_client.register_model(
                            model_name=r,
                            litellm_model=litellm_model,
                            api_key=fallback_source.api_key or None,
                            api_base=fallback_source.api_base or None,
                            model_info={
                                "mode": "chat",
                                "db_model_id": fallback_source.id,
                                "provider": fallback_source.provider,
                                "physical_model": fallback_source.model_id,
                                "context_window": fallback_source.context_window,
                            },
                        )
            elif allowed_nodes:
                fallback_node = allowed_nodes[0]
                f_api_base = fallback_node.get("api_base", "").rstrip("/")
                f_v1 = f_api_base if f_api_base.endswith("/v1") else f"{f_api_base}/v1"
                f_served = fallback_node.get("served_model_name") or "coding-model"
                for r in standard_roles:
                    if r not in active_roles:
                        litellm_client.register_model(
                            model_name=r,
                            litellm_model=f"openai/{f_served}",
                            api_key="sk-vllm-dummy",
                            api_base=f_v1,
                            model_info={
                                "mode": "chat",
                                "node_id": fallback_node.get("node_id"),
                                "provider": "local_node",
                                "physical_model": fallback_node.get("model_name"),
                                "description": f"Fallback role {r} mapped to node {fallback_node.get('node_id')}",
                            },
                        )

            logger.info(f"Reconciled LiteLLM models: {synced_count} active, {deleted_count} purged.")
            return {"active": synced_count, "purged": deleted_count, "success": True}
        except Exception as e:
            logger.error(f"Error during LiteLLM model reconciliation: {e}")
            return {"error": str(e), "success": False}

    @classmethod
    def list_all(cls, db: Session) -> Dict[str, Any]:
        """
        Returns all configured models from DB and active hardware GPU nodes from Registry,
        ensuring bidirectional synchronization with LiteLLM Proxy.
        """
        active_nodes = registry_client.get_nodes()
        litellm_models = litellm_client.get_registered_models()
        litellm_model_names = {lm.get("model_name") for lm in litellm_models if lm.get("model_name")}

        now = datetime.now(timezone.utc).isoformat()
        active_node_ids = set()

        # 1. Mirror active GPU nodes into ManagedModelModel in Postgres
        for node in active_nodes:
            nid = node.get("node_id")
            if not nid:
                continue
            active_node_ids.add(nid)
            db_id = f"node_{nid}"
            is_healthy = (node.get("status") == "healthy")
            served_name = node.get("served_model_name") or "coding-model"

            existing = db.query(ManagedModelModel).filter(ManagedModelModel.id == db_id).first()
            if not existing:
                new_node_model = ManagedModelModel(
                    id=db_id,
                    name=f"نود {nid}",
                    provider="local_node",
                    model_id=node.get("model_name") or served_name,
                    api_key="",
                    api_base=node.get("api_base") or "",
                    assigned_role=served_name,
                    is_enabled=is_healthy,
                    context_window=4096,
                    created_at=now,
                    updated_at=now,
                )
                db.add(new_node_model)
                if is_healthy and served_name not in litellm_model_names:
                    cls._sync_node_to_litellm(node)
                    litellm_model_names.add(served_name)
                    litellm_model_names.add("general-model")
            else:
                # If hardware is offline, force disable
                if not is_healthy:
                    existing.is_enabled = False
                # If hardware is healthy, keep existing.is_enabled (respecting user's manual toggle switch)
                existing.api_base = node.get("api_base") or existing.api_base
                existing.model_id = node.get("model_name") or existing.model_id
                existing.assigned_role = served_name
                existing.updated_at = now

                # If healthy and enabled, ensure synced to LiteLLM
                if existing.is_enabled and served_name not in litellm_model_names:
                    cls._sync_node_to_litellm(node)
                    litellm_model_names.add(served_name)
                    litellm_model_names.add("general-model")

        # 2. Deactivate any local_node records whose node is no longer in active_nodes
        stale_nodes = db.query(ManagedModelModel).filter(
            ManagedModelModel.provider == "local_node",
            ManagedModelModel.is_enabled == True
        ).all()
        for sn in stale_nodes:
            node_key = sn.id.replace("node_", "", 1)
            if node_key not in active_node_ids:
                sn.is_enabled = False
                sn.updated_at = now

        db.commit()

        # 3. Retrieve all models from DB
        db_models = db.query(ManagedModelModel).order_by(ManagedModelModel.created_at.desc()).all()
        models_list = []
        for m in db_models:
            d = m.to_dict(mask_key=True)
            # Flag if this model's role or modelId is actively registered in LiteLLM
            d["litellmSynced"] = (m.assigned_role in litellm_model_names or m.model_id in litellm_model_names)
            models_list.append(d)

        enabled_count = len([m for m in models_list if m["isEnabled"]])
        return {
            "models": models_list,
            "activeNodes": active_nodes,
            "summary": {
                "totalModels": len(models_list),
                "enabledModels": enabled_count,
                "activeNodesCount": len([n for n in active_nodes if n.get("status") == "healthy"]),
                "litellmModelsCount": len(litellm_model_names),
                "litellmConnected": bool(litellm_model_names or litellm_client.health_check()),
                "inSync": True,
            }
        }

    @classmethod
    def create_model(
        cls,
        name: str,
        provider: str,
        model_id: str,
        assigned_role: str,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        context_window: int = 32768,
        is_enabled: bool = True,
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """Creates a new model in the DB and registers it in LiteLLM."""
        if not db:
            raise ValueError("Database session required")

        clean_name = (name or model_id).strip()
        mod_id = f"mod_{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()

        new_model = ManagedModelModel(
            id=mod_id,
            name=clean_name,
            provider=provider.lower().strip(),
            model_id=model_id.strip(),
            api_key=api_key.strip() if api_key else "",
            api_base=api_base.strip() if api_base else "",
            assigned_role=assigned_role.strip(),
            is_enabled=is_enabled,
            context_window=context_window or 32768,
            created_at=now,
            updated_at=now,
        )
        db.add(new_model)
        db.commit()
        db.refresh(new_model)

        # Full sync with LiteLLM Proxy
        cls.reconcile_all_models_with_litellm(db)

        return new_model.to_dict(mask_key=True)

    @classmethod
    def toggle_model(cls, model_id: str, is_enabled: Optional[bool], db: Session) -> Dict[str, Any]:
        """Toggles model enabled/disabled state and syncs LiteLLM routing."""
        m = db.query(ManagedModelModel).filter(ManagedModelModel.id == model_id).first()
        if not m:
            raise ValueError("Model not found")

        if is_enabled is not None:
            m.is_enabled = is_enabled
        else:
            m.is_enabled = not m.is_enabled

        m.updated_at = datetime.now(timezone.utc).isoformat()
        db.commit()
        db.refresh(m)

        # Full sync with LiteLLM Proxy
        cls.reconcile_all_models_with_litellm(db)

        return m.to_dict(mask_key=True)

    @classmethod
    def delete_model(cls, model_id: str, db: Session) -> Dict[str, Any]:
        """Deletes model from database and reconciles LiteLLM Proxy."""
        m = db.query(ManagedModelModel).filter(ManagedModelModel.id == model_id).first()
        if not m:
            return {"deleted": True, "id": model_id}

        db.delete(m)
        db.commit()

        # Full sync with LiteLLM Proxy
        cls.reconcile_all_models_with_litellm(db)

        return {"deleted": True, "id": model_id}

    @classmethod
    def test_model(cls, model_id: str, db: Session) -> Dict[str, Any]:
        """Sends a live test request to the model via LiteLLM and returns latency & response."""
        import time
        m = db.query(ManagedModelModel).filter(ManagedModelModel.id == model_id).first()
        if not m:
            raise ValueError("Model not found")

        if not m.is_enabled:
            return {
                "success": False,
                "status": "disabled",
                "error": "این مدل در حال حاضر خاموش است. ابتدا آن را روشن کنید.",
                "latencyMs": 0,
            }

        start_time = time.time()
        try:
            # First try completion test via assigned_role (e.g. coding-model, general-model)
            test_targets = [m.assigned_role]
            if m.model_id and m.model_id not in test_targets:
                test_targets.append(m.model_id)

            res = None
            used_target = m.assigned_role
            for target in test_targets:
                used_target = target
                res = litellm_client.chat_completion(
                    model=target,
                    messages=[{"role": "user", "content": "پاسخ کوتاه بده: وضعیت سیستم فعال است."}],
                    user_id="healthcheck_admin",
                    metadata={"test_ping": True, "model_id": m.id},
                )
                if res and "choices" in res and len(res["choices"]) > 0:
                    break

            latency_ms = round((time.time() - start_time) * 1000, 1)

            if res and "choices" in res and len(res["choices"]) > 0:
                reply = res["choices"][0]["message"].get("content", "")
                return {
                    "success": True,
                    "status": "healthy",
                    "latencyMs": latency_ms,
                    "modelName": m.name,
                    "modelId": m.model_id,
                    "assignedRole": m.assigned_role,
                    "testedTarget": used_target,
                    "replySnippet": reply.strip(),
                }
            else:
                return {
                    "success": False,
                    "status": "error",
                    "latencyMs": latency_ms,
                    "error": str(res.get("error", "پاسخی از مدل دریافت نشد.") if res else "پاسخی دریافت نشد."),
                }
        except Exception as e:
            latency_ms = round((time.time() - start_time) * 1000, 1)
            return {
                "success": False,
                "status": "error",
                "latencyMs": latency_ms,
                "error": str(e),
            }

    @classmethod
    def ensure_default_models(cls, db: Session) -> None:
        """Runs model reconciliation on system startup."""
        cls.reconcile_all_models_with_litellm(db)


managed_model_service = ManagedModelService()
