"""
Dashboard, Models, and Limits business logic service.
"""

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.integrations.litellm import litellm_client
from app.integrations.registry import registry_client
from app.models.organization import OrganizationModel
from app.models.team import TeamModel
from app.models.user import UserModel


class DashboardService:
    @staticmethod
    def get_dashboard(user: Dict[str, Any], db: Session) -> Dict[str, Any]:
        role = user.get("role", "super_admin")
        user_org_id = user.get("organizationId")
        user_team_id = user.get("teamId")

        litellm_health = litellm_client.health_check() or {"status": "connected"}
        active_nodes = registry_client.get_nodes()

        if role == "super_admin":
            total_orgs = db.query(OrganizationModel).count()
            total_teams = db.query(TeamModel).count()
            total_users = db.query(UserModel).count()
            orgs = db.query(OrganizationModel).all()
            token_limit = sum(o.token_limit for o in orgs) or settings.DB_LIMITS.get("workspaceTokenLimit", 20000000)
            users_all = db.query(UserModel).all()
            total_tokens = sum(u.used_tokens for u in users_all)
        elif role == "org_admin":
            total_orgs = 1
            teams = db.query(TeamModel).filter(TeamModel.organization_id == user_org_id).all()
            total_teams = len(teams)
            total_users = db.query(UserModel).filter(UserModel.organization_id == user_org_id).count()
            org_users = db.query(UserModel).filter(UserModel.organization_id == user_org_id).all()
            total_tokens = sum(u.used_tokens for u in org_users)
            org_obj = db.query(OrganizationModel).filter(OrganizationModel.id == user_org_id).first()
            token_limit = org_obj.token_limit if org_obj else 5000000
        else:
            total_orgs = 1
            total_teams = 1
            total_users = db.query(UserModel).filter(UserModel.team_id == user_team_id).count()
            team_obj = db.query(TeamModel).filter(TeamModel.id == user_team_id).first()
            total_tokens = team_obj.used_tokens if team_obj else 0
            token_limit = team_obj.token_limit if team_obj else 2000000

        used_percent = min(100, int((total_tokens / max(1, token_limit)) * 100))

        return {
            "role": role,
            "currentUser": user,
            "requestsToday": 0,
            "tokensThisMonth": total_tokens,
            "activeUsers": len(active_nodes),
            "totalUsers": total_users,
            "totalOrganizations": total_orgs,
            "totalTeams": total_teams,
            "averageResponseMs": 0,
            "requestsLastHour": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            "maxRps": settings.DB_LIMITS.get("maxRps", 20),
            "defaultRps": settings.DB_LIMITS.get("defaultRps", 5),
            "inferenceConcurrency": settings.DB_LIMITS.get("inferenceConcurrency", 32),
            "maxInputChars": settings.DB_LIMITS.get("maxInputChars", 8000),
            "maxOutputTokens": settings.DB_LIMITS.get("maxOutputTokens", 4096),
            "maxPdfPages": settings.DB_LIMITS.get("maxPdfPages", 20),
            "perAccountTokenLimit": settings.DB_LIMITS.get("perAccountTokenLimit", 500000),
            "workspaceTokenLimit": token_limit,
            "tokenUsagePercent": used_percent,
            "messagesPerHour": settings.DB_LIMITS.get("messagesPerHour", 120),
            "messagesUsedLastHour": 0,
            "litellm": {
                "status": "healthy" if litellm_health else "online",
                "url": settings.LITELLM_URL,
                "masterKeyPrefix": settings.LITELLM_MASTER_KEY[:8] + "...",
                "activeVirtualTeams": total_teams,
            },
            "models": [
                {
                    "id": n.get("served_model_name", "general-model"),
                    "name": n.get("model_name", "Qwen 2.5"),
                    "detail": f"نود {n.get('node_id')} ({n.get('hardware', {}).get('gpus', [{}])[0].get('name', 'NVIDIA GPU') if n.get('hardware', {}).get('gpus') else 'کارت گرافیک فعال'})",
                    "nodeId": n.get("node_id"),
                    "gpu": n.get("hardware", {}).get("gpus", [{}])[0].get("name", "NVIDIA GPU") if n.get("hardware", {}).get("gpus") else "کارت گرافیک فعال",
                    "ip": n.get("ip", "127.0.0.1"),
                    "port": n.get("port", 8000),
                    "enabled": True,
                    "isDefault": True,
                    "latencyMs": 140,
                    "contextWindow": 32768,
                }
                for n in active_nodes
            ],
            "activeNodes": active_nodes,
        }

    @staticmethod
    def get_models() -> List[Dict[str, Any]]:
        active_nodes = registry_client.get_nodes()
        if active_nodes:
            live_models = []
            for n in active_nodes:
                gpus = n.get("hardware", {}).get("gpus", [])
                gpu_desc = gpus[0].get("name", "NVIDIA GPU") if gpus else "کارت گرافیک فعال"
                live_models.append({
                    "id": n.get("served_model_name", "general-model"),
                    "name": n.get("model_name", "Qwen 2.5"),
                    "detail": f"نود {n.get('node_id')} ({gpu_desc})",
                    "nodeId": n.get("node_id"),
                    "gpu": gpu_desc,
                    "ip": n.get("ip", "127.0.0.1"),
                    "port": n.get("port", 8000),
                    "enabled": True,
                    "isDefault": True,
                    "latencyMs": 140,
                    "contextWindow": 32768,
                })
            return live_models
        return []

    @staticmethod
    def get_limits(user: Optional[Dict[str, Any]], db: Session) -> Dict[str, Any]:
        user_info = user or {}
        user_id = user_info.get("id")
        user_used_tokens = 0
        user_token_limit = 500000
        user_role = user_info.get("role", "user")

        if user_id:
            usr = db.query(UserModel).filter(UserModel.id == user_id).first()
            if usr:
                user_used_tokens = usr.used_tokens
                user_token_limit = usr.token_limit
                user_role = usr.role

        user_team_id = user_info.get("teamId")
        team_used = 0
        team_limit = 2000000
        team_name = ""
        if user_team_id:
            team_obj = db.query(TeamModel).filter(TeamModel.id == user_team_id).first()
            if team_obj:
                team_used = team_obj.used_tokens
                team_limit = team_obj.token_limit
                team_name = team_obj.name

        user_org_id = user_info.get("organizationId")
        org_used = 0
        org_limit = 10000000
        org_name = ""
        if user_org_id:
            org_obj = db.query(OrganizationModel).filter(OrganizationModel.id == user_org_id).first()
            if org_obj:
                org_used = sum(t.used_tokens for t in org_obj.teams) if org_obj.teams else 0
                org_limit = org_obj.token_limit
                org_name = org_obj.name

        if user_role == "super_admin":
            all_users = db.query(UserModel).all()
            all_orgs = db.query(OrganizationModel).all()
            cluster_used = sum(u.used_tokens for u in all_users)
            cluster_limit = sum(o.token_limit for o in all_orgs) or settings.DB_LIMITS.get("workspaceTokenLimit", 20000000)
        else:
            cluster_used = org_used
            cluster_limit = org_limit

        return {
            "role": user_role,
            "maxConversations": 50,
            "requestsPerWindow": settings.DB_LIMITS.get("maxRps", 20) * 60,
            "requestWindowMinutes": 1,
            "maxInputChars": settings.DB_LIMITS.get("maxInputChars", 8000),
            "maxOutputTokens": settings.DB_LIMITS.get("maxOutputTokens", 4096),
            "maxHistoryMessages": 100,
            "maxConcurrentStreams": settings.DB_LIMITS.get("inferenceConcurrency", 32),
            "conversationRetentionDays": 30,
            "maxPdfAttachments": 5,
            "maxPdfSizeBytes": 20 * 1024 * 1024,
            "maxPdfPages": settings.DB_LIMITS.get("maxPdfPages", 20),
            "mcpDefaultRpm": settings.DB_LIMITS.get("defaultRps", 5) * 60,
            "mcpDefaultRps": settings.DB_LIMITS.get("defaultRps", 5),
            "mcpMaxRpm": settings.DB_LIMITS.get("maxRps", 20) * 60,
            "mcpMaxRps": settings.DB_LIMITS.get("maxRps", 20),
            "totalTokensUsed": user_used_tokens,
            "totalTokenLimit": user_token_limit,
            "userTokensUsed": user_used_tokens,
            "userTokenLimit": user_token_limit,
            "teamTokensUsed": team_used,
            "teamTokenLimit": team_limit,
            "teamName": team_name,
            "orgTokensUsed": org_used,
            "orgTokenLimit": org_limit,
            "orgName": org_name,
            "clusterTokensUsed": cluster_used,
            "clusterTokenLimit": cluster_limit,
            "messagesUsedThisHour": 0,
            "messagesPerHour": settings.DB_LIMITS.get("messagesPerHour", 120),
            **settings.DB_LIMITS,
        }


dashboard_service = DashboardService()
