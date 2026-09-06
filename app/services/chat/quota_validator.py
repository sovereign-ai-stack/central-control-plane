"""
Chat Quota Validator.
Enforces 3-tier token quota limits (Organization -> Team -> User)
and returns an SSE StreamingResponse if any limit is exceeded.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, Optional
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.organization import OrganizationModel
from app.models.team import TeamModel
from app.models.user import UserModel


class ChatQuotaValidator:
    """Validates organization, team, and user token quotas before processing chat requests."""

    @staticmethod
    def check_quotas(
        user: Dict[str, Any],
        db: Session,
        is_fa: bool,
        req_id: str,
    ) -> Optional[StreamingResponse]:
        """
        Checks 3-tier token quotas.
        Returns a StreamingResponse with quota_exceeded event if limits are exhausted,
        or None if quota checks pass.
        """
        user_org = user.get("organizationId")
        user_team = user.get("teamId")
        user_id = user.get("id")

        # 1. Check Organization-Level Token Quota
        if user_org:
            org_obj = db.query(OrganizationModel).filter(OrganizationModel.id == user_org).first()
            if org_obj:
                org_total_used = (
                    db.query(func.coalesce(func.sum(TeamModel.used_tokens), 0))
                    .filter(TeamModel.organization_id == user_org)
                    .scalar()
                    or 0
                )
                if org_total_used >= org_obj.token_limit:
                    async def org_quota_stream() -> AsyncGenerator[str, None]:
                        err_txt = (
                            f"⚠️ **اتمام سهمیه توکن سازمان:**\n\n"
                            f"سقف توکن‌های ماهانه سازمان «{org_obj.name}» (مجموعاً {org_obj.token_limit:,} توکن) به پایان رسیده است. "
                            f"جهت تمدید منابع با مدیر کل سامانه تماس حاصل فرمایید."
                            if is_fa else
                            f"⚠️ **Organization Quota Exceeded:**\n\n"
                            f"The monthly token quota for organization \"{org_obj.name}\" ({org_obj.token_limit:,} tokens) "
                            f"has been exhausted. Please contact your system administrator to extend resources."
                        )
                        yield f"event: delta\ndata: {json.dumps({'type': 'delta', 'requestId': req_id, 'text': err_txt, 'content': err_txt}, ensure_ascii=False)}\n\n"
                        yield f"event: complete\ndata: {json.dumps({'type': 'complete', 'status': 'quota_exceeded', 'message': {'id': f'msg_{uuid.uuid4().hex[:8]}', 'role': 'assistant', 'content': err_txt, 'createdAt': datetime.now(timezone.utc).isoformat()}}, ensure_ascii=False)}\n\n"

                    return StreamingResponse(org_quota_stream(), media_type="text/event-stream")

        # 2. Check Team-Level Token Quota
        if user_team and user_team != "global":
            team_obj = db.query(TeamModel).filter(TeamModel.id == user_team).first()
            if team_obj and team_obj.used_tokens >= team_obj.token_limit:
                async def team_quota_stream() -> AsyncGenerator[str, None]:
                    err_txt = (
                        f"⚠️ **اتمام سهمیه توکن تیم:**\n\n"
                        f"سقف ماهانه توکن‌های تیم «{team_obj.name}» ({team_obj.token_limit:,} توکن) تکمیل شده است. "
                        f"لطفاً با مدیر سازمان هماهنگ فرمایید."
                        if is_fa else
                        f"⚠️ **Team Quota Exceeded:**\n\n"
                        f"The monthly token quota for team \"{team_obj.name}\" ({team_obj.token_limit:,} tokens) "
                        f"has been exhausted. Please coordinate with your organization admin."
                    )
                    yield f"event: delta\ndata: {json.dumps({'type': 'delta', 'requestId': req_id, 'text': err_txt, 'content': err_txt}, ensure_ascii=False)}\n\n"
                    yield f"event: complete\ndata: {json.dumps({'type': 'complete', 'status': 'quota_exceeded', 'message': {'id': f'msg_{uuid.uuid4().hex[:8]}', 'role': 'assistant', 'content': err_txt, 'createdAt': datetime.now(timezone.utc).isoformat()}}, ensure_ascii=False)}\n\n"

                return StreamingResponse(team_quota_stream(), media_type="text/event-stream")

        # 3. Check User-Level Token Quota
        user_db = db.query(UserModel).filter(UserModel.id == user_id).first()
        if user_db and user_db.token_limit and user_db.used_tokens >= user_db.token_limit:
            async def user_quota_stream() -> AsyncGenerator[str, None]:
                err_txt = (
                    f"⚠️ **اتمام سهمیه کاربری:**\n\n"
                    f"سهمیه اختصاصی ماهانه حساب شما ({user_db.token_limit:,} توکن) به اتمام رسیده است."
                    if is_fa else
                    f"⚠️ **Personal Quota Exceeded:**\n\n"
                    f"Your individual monthly token limit ({user_db.token_limit:,} tokens) has been reached."
                )
                yield f"event: delta\ndata: {json.dumps({'type': 'delta', 'requestId': req_id, 'text': err_txt, 'content': err_txt}, ensure_ascii=False)}\n\n"
                yield f"event: complete\ndata: {json.dumps({'type': 'complete', 'status': 'quota_exceeded', 'message': {'id': f'msg_{uuid.uuid4().hex[:8]}', 'role': 'assistant', 'content': err_txt, 'createdAt': datetime.now(timezone.utc).isoformat()}}, ensure_ascii=False)}\n\n"

            return StreamingResponse(user_quota_stream(), media_type="text/event-stream")

        return None
