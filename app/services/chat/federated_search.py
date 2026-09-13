"""
Federated Vector Search Service.
Executes multi-tenant document retrieval across isolated organization shards
and the global shared knowledge shard in Weaviate.
"""

import os
import time
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.models.document import DocumentModel
from rag import rag_service

MIN_SIMILARITY_SCORE = float(os.getenv("RAG_MIN_SIMILARITY_SCORE", "0.52"))



class FederatedSearchService:
    """Performs multi-tenant vector search with deduplication and RBAC scoping."""

    @staticmethod
    def _execute_search_pass(
        search_text: str,
        user: Dict[str, Any],
        user_org: Optional[str],
        user_team: Optional[str],
        user_id: Optional[str],
        db: Session,
    ) -> Dict[str, Any]:
        citations: List[Dict[str, Any]] = []
        context_parts: List[str] = []
        is_super = (user.get("role") == "super_admin")
        allowed_teams = [user_team, "global"] if user_team else ["global"]

        # 1. Identify target organizations to search
        org_targets = set()
        if user_org and user_org not in ["global", "org_global", ""]:
            org_targets.add(user_org)
        if is_super:
            try:
                doc_orgs = db.query(DocumentModel.organization_id).distinct().all()
                for (d_org,) in doc_orgs:
                    if d_org and d_org not in ["global", "org_global", ""]:
                        org_targets.add(d_org)
            except Exception as e:
                logger.warning(f"Error querying distinct doc orgs for super admin: {e}")

        retrieval_errors: List[str] = []

        # 2. Search target organizations
        for org_id in org_targets:
            try:
                target_teams = list(allowed_teams)
                if is_super:
                    try:
                        doc_teams = db.query(DocumentModel.team_id).filter(DocumentModel.organization_id == org_id).distinct().all()
                        for (d_team,) in doc_teams:
                            if d_team and d_team not in target_teams:
                                target_teams.append(d_team)
                    except Exception as te:
                        logger.debug(f"Error querying teams for org {org_id}: {te}")

                chunks_org = rag_service.retrieve(
                    query=search_text,
                    organization_id=org_id,
                    team_id=user_team if not is_super else None,
                    allowed_team_ids=target_teams,
                    user_id=user_id,
                    top_k=4,
                )
                for c in chunks_org:
                    if c.get("score", 0) >= MIN_SIMILARITY_SCORE and not any(
                        x.get("snippet", "")[:80] == c.get("content", "")[:80] for x in citations
                    ):
                        citations.append({
                            "claimIndex": len(citations),
                            "title": c.get("title", "سند سازمانی"),
                            "section": c.get("section", "بخش ۱"),
                            "snippet": (c.get("content", "")[:350] + "...") if len(c.get("content", "")) > 350 else c.get("content", ""),
                            "url": "/admin#knowledge",
                            "supportStatus": "supported",
                            "confidenceScore": round(float(c.get("score", 0)), 4),
                        })
                        context_parts.append(f"[{c.get('title')} - {c.get('section')}]\n{c.get('content')}")
            except Exception as e:
                logger.error(f"[FederatedSearch] Failed querying org '{org_id}' in RAG: {e}", exc_info=True)
                retrieval_errors.append(f"org:{org_id}:{str(e)}")

        # 3. Global Shared Knowledge Shard
        try:
            global_teams = ["global"]
            if is_super:
                try:
                    doc_teams = db.query(DocumentModel.team_id).filter(
                        (DocumentModel.organization_id == "global") | (DocumentModel.organization_id == None)
                    ).distinct().all()
                    for (d_team,) in doc_teams:
                        if d_team and d_team not in global_teams:
                            global_teams.append(d_team)
                except Exception as gte:
                    logger.debug(f"Error querying global teams: {gte}")

            chunks_global = rag_service.retrieve(
                query=search_text,
                organization_id="global",
                team_id="global",
                allowed_team_ids=global_teams,
                user_id=user_id,
                top_k=4,
            )
            for c in chunks_global:
                if c.get("score", 0) >= MIN_SIMILARITY_SCORE and not any(
                    x.get("snippet", "")[:80] == c.get("content", "")[:80] for x in citations
                ):
                    citations.append({
                        "claimIndex": len(citations),
                        "title": c.get("title", "سند سازمانی"),
                        "section": c.get("section", "بخش ۱"),
                        "snippet": (c.get("content", "")[:350] + "...") if len(c.get("content", "")) > 350 else c.get("content", ""),
                        "url": "/admin#knowledge",
                        "supportStatus": "supported",
                        "confidenceScore": round(float(c.get("score", 0)), 4),
                    })
                    context_parts.append(f"[{c.get('title')} - {c.get('section')}]\n{c.get('content')}")
        except Exception as e:
            logger.error(f"[FederatedSearch] Failed querying global shard in RAG: {e}", exc_info=True)
            retrieval_errors.append(f"global:{str(e)}")

        total_shards = max(1, len(org_targets) + 1)
        if len(retrieval_errors) >= total_shards:
            status = "failed"
        elif retrieval_errors:
            status = "degraded"
        else:
            status = "ok"

        return {
            "citations": citations,
            "context": "\n\n".join(context_parts),
            "status": status,
            "errors": retrieval_errors,
        }

    @classmethod
    def search(
        cls,
        query: str,
        contextual_query: str,
        user: Dict[str, Any],
        db: Session,
        has_history: bool = False,
    ) -> Dict[str, Any]:
        """
        Executes primary search with fallback to contextual multi-turn query if no citations found.
        """
        user_org = user.get("organizationId")
        user_team = user.get("teamId")
        user_id = user.get("id")

        t_start = time.time()
        real_citations = []
        rag_context_text = ""
        overall_status = "ok"
        all_errors = []

        try:
            res = cls._execute_search_pass(query, user, user_org, user_team, user_id, db)
            if res:
                overall_status = res.get("status", "ok")
                all_errors.extend(res.get("errors", []))
                if res.get("citations"):
                    real_citations = res["citations"]
                    rag_context_text = res.get("context", "")

            # Fallback to contextual rewritten query
            if not real_citations and has_history and contextual_query != query:
                res_ctx = cls._execute_search_pass(contextual_query, user, user_org, user_team, user_id, db)
                if res_ctx:
                    if res_ctx.get("status") == "failed" and overall_status == "ok":
                        overall_status = "failed"
                    all_errors.extend(res_ctx.get("errors", []))
                    if res_ctx.get("citations"):
                        real_citations = res_ctx["citations"]
                        rag_context_text = res_ctx.get("context", "")
        except Exception as e:
            logger.error(f"[FederatedSearch] Critical error during federated search: {e}", exc_info=True)
            overall_status = "failed"
            all_errors.append(str(e))

        latency_ms = round((time.time() - t_start) * 1000, 2)
        return {
            "citations": real_citations,
            "context": rag_context_text,
            "latency_ms": latency_ms,
            "retrieval_status": overall_status,
            "retrieval_errors": all_errors,
        }
