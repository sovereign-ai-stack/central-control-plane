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
    def reconcile_all_models_with_litellm(cls, db: Session) -> Dict[str, Any]:
        """
        Full synchronization between Database and LiteLLM Proxy:
        1. Purges all orphaned, static dummy, or phantom models from LiteLLM.
        2. Registers all active models into LiteLLM Proxy under their respective system roles.
        """
        try:
            db_models = db.query(ManagedModelModel).all()
            enabled_models = [m for m in db_models if m.is_enabled]
            enabled_map = {m.id: m for m in enabled_models}

            # 1. Fetch current models from LiteLLM Proxy
            litellm_models = litellm_client.get_registered_models()
            deleted_count = 0

            # 2. Purge stale/orphaned models from LiteLLM only if DB models exist
            if enabled_models:
                for lm in litellm_models:
                    m_info = lm.get("model_info", {})
                    lid = m_info.get("id")
                    db_mid = m_info.get("db_model_id")

                    if not db_mid or db_mid not in enabled_map or lm.get("model_name") != enabled_map[db_mid].assigned_role:
                        if lid:
                            litellm_client.delete_model_by_id(lid)
                            deleted_count += 1

            # 3. Register/Update all enabled models into LiteLLM
            synced_count = 0
            for m in enabled_models:
                cls.sync_model_to_litellm(m)
                synced_count += 1

            # 4. Guarantee all standard roles have a working backend dynamically
            standard_roles = ["general-model", "coding-model", "reasoning-model", "rag-model"]
            active_roles = {m.assigned_role for m in enabled_models}
            fallback_source = enabled_models[0] if enabled_models else None

            if fallback_source:
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

            logger.info(f"Reconciled LiteLLM models: {synced_count} active, {deleted_count} purged.")
            return {"active": synced_count, "purged": deleted_count, "success": True}
        except Exception as e:
            logger.error(f"Error during LiteLLM model reconciliation: {e}")
            return {"error": str(e), "success": False}

    @classmethod
    def list_all(cls, db: Session) -> Dict[str, Any]:
        """Returns all configured models from DB and active hardware GPU nodes from Registry."""
        db_models = db.query(ManagedModelModel).order_by(ManagedModelModel.created_at.desc()).all()
        active_nodes = registry_client.get_nodes()

        models_list = [m.to_dict(mask_key=True) for m in db_models]

        return {
            "models": models_list,
            "activeNodes": active_nodes,
            "summary": {
                "totalModels": len(models_list),
                "enabledModels": len([m for m in models_list if m["isEnabled"]]),
                "activeNodesCount": len(active_nodes),
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
            # Send completion test to LiteLLM for this assigned role
            res = litellm_client.chat_completion(
                model=m.assigned_role,
                messages=[{"role": "user", "content": "پاسخ کوتاه بده: وضعیت سیستم فعال است."}],
                user_id="healthcheck_admin",
                metadata={"test_ping": True, "model_id": m.id},
            )
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
