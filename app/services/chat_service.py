"""
Chat Streaming Business Logic Orchestrator.
Coordinates 3-tier token quota validation, SSE progress events, in-process RAG & Semantic Router integration,
vector citations, LiteLLM streaming with <think> boundary tracking, and Langfuse observability.
"""

import asyncio
import json
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, Optional
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.integrations.langfuse_client import PipelineTrace
from app.integrations.litellm import litellm_client
from app.integrations.semantic import semantic_client
from app.models.managed_model import ManagedModelModel
from app.models.organization import OrganizationModel
from app.models.team import TeamModel
from app.router.engine import semantic_router_engine
from app.schemas.chat import SendMessageRequest
from app.services.chat import (
    ChatConversationManager,
    ChatOfflineFallback,
    ChatPromptBuilder,
    ChatQuotaValidator,
    FederatedSearchService,
    StarterCannedService,
    StreamBufferParser,
)


class ChatService:
    """High-level orchestrator for multi-tenant chat streaming."""

    @staticmethod
    def process_chat_stream(
        payload: SendMessageRequest,
        user: Dict[str, Any],
        db: Session,
    ) -> StreamingResponse:
        conv_id = payload.conversation_id or payload.conversationId or f"conv_{uuid.uuid4().hex[:12]}"
        user_org = user.get("organizationId")
        user_team = user.get("teamId")
        user_id = user.get("id")
        lang = (payload.language or "fa").lower()
        is_fa = (lang == "fa")
        req_id = f"req_{uuid.uuid4().hex[:8]}"

        # 1. Enforce 3-Tier Quota Limits (Org -> Team -> User)
        quota_response = ChatQuotaValidator.check_quotas(
            user=user,
            db=db,
            is_fa=is_fa,
            req_id=req_id,
        )
        if quota_response:
            return quota_response

        # 2. Prepare Conversation & Record User Prompt
        conv, messages_list, initial_token_deduct = ChatConversationManager.prepare_conversation(
            conv_id=conv_id,
            message=payload.message,
            lang=lang,
            user_id=user_id,
            user_team=user_team,
            db=db,
            reply_to_id=payload.reply_to_message_id or payload.replyToMessageId,
            reply_to_snippet=payload.reply_to_snippet or payload.replyToSnippet,
        )

        async def event_generator() -> AsyncGenerator[str, None]:
            t_start_request = time.time()
            user_name = user.get("name", "کاربر گرامی" if is_fa else "Valued User")
            explicit_use_rag = payload.use_rag if payload.use_rag is not None else payload.useRag

            # Initialize Langfuse Observability Trace
            trace = PipelineTrace(
                name="chat_interaction",
                user_id=user.get("email") or str(user_id),
                session_id=conv_id,
                input_data=payload.message,
                metadata={
                    "organization_id": user_org,
                    "team_id": user_team,
                    "user_name": user_name,
                    "language": "fa" if is_fa else "en",
                    "request_id": req_id,
                    "explicit_use_rag": explicit_use_rag,
                },
                tags=["production", "fa" if is_fa else "en"],
            )

            try:
                # 2.5 Intercept 4 Starter Actions with Instant Authoritative Guide & Live Status
                canned_key = StarterCannedService.match(payload.message)
                if canned_key:
                    canned_label_map = {
                        "node_registration": "راهنمای اتصال نودهای پردازش گرافیکی",
                        "node_health": "پایش سلامت نودها و وضعیت کارت گرافیک",
                        "routing_and_rag": "معماری مسیریابی هوشمند و RAG",
                        "cluster_status": "گزارش زنده وضعیت سرویس‌های کلاستر",
                    }
                    tool_label = canned_label_map.get(canned_key, "راهنمای مهندسی کلاستر")
                    yield f"event: tool\ndata: {json.dumps({'type': 'tool', 'requestId': req_id, 'name': 'cluster_canned_guide', 'label': tool_label, 'status': 'completed', 'summary': 'استخراج بلادرنگ از مستندات و تله‌متری کلاستر'}, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0.02)

                    canned_real_text = ""
                    canned_thinking_text = ""
                    async for ev_type, sse_chunk, raw_text in StarterCannedService.stream_canned_response(
                        key=canned_key,
                        user=user,
                        db=db,
                        is_fa=is_fa,
                        req_id=req_id,
                    ):
                        if ev_type == "thinking":
                            canned_thinking_text += raw_text
                        elif ev_type == "delta":
                            canned_real_text += raw_text
                        yield sse_chunk

                    clean_canned_content = canned_real_text.strip()
                    clean_canned_thinking = canned_thinking_text.strip()
                    assistant_message_obj = {
                        "id": f"msg_{uuid.uuid4().hex[:8]}",
                        "role": "assistant",
                        "content": clean_canned_content,
                        "reasoningContent": clean_canned_thinking if clean_canned_thinking else None,
                        "status": "complete",
                        "citations": [],
                        "createdAt": datetime.now(timezone.utc).isoformat(),
                    }
                    yield f"event: complete\ndata: {json.dumps({'type': 'complete', 'status': 'complete', 'message': assistant_message_obj}, ensure_ascii=False)}\n\n"

                    total_duration_ms = round((time.time() - t_start_request) * 1000, 2)
                    trace.update(
                        input_data=payload.message,
                        output_data=clean_canned_content,
                        metadata={
                            "route": "starter_guide",
                            "canned_key": canned_key,
                            "total_duration_ms": total_duration_ms,
                        },
                        tags=["starter_guide", canned_key],
                    )
                    ChatConversationManager.finalize_conversation(
                        conv_id=conv_id,
                        assistant_message_obj=assistant_message_obj,
                        remaining_tokens=0,
                        user_id=user_id,
                        user_team=user_team,
                    )
                    return

                # 3. Classify Intent via Modular Semantic Router Engine
                t_start_route = time.time()
                route_result = semantic_router_engine.classify(
                    query=payload.message,
                    explicit_use_rag=explicit_use_rag,
                    semantic_client=semantic_client,
                    user_id=user.get("id", "u_admin"),
                    session_id=conv_id,
                )
                detected_route = route_result.route
                # Strict Rule: Under NO circumstances allow RAG unless explicit_use_rag is explicitly True
                if explicit_use_rag is not True and detected_route == "rag":
                    detected_route = "general"
                routing_method = route_result.method
                confidence_score = route_result.confidence
                matched_patterns = route_result.matched_patterns

                route_latency_ms = round((time.time() - t_start_route) * 1000, 2)
                trace.span(
                    name="semantic_routing",
                    input_data={"query": payload.message, "explicit_use_rag": explicit_use_rag},
                    output_data={
                        "route": detected_route,
                        "routing_method": routing_method,
                        "confidence": confidence_score,
                        "matched_patterns": matched_patterns,
                    },
                    metadata={"duration_ms": route_latency_ms, "explicit_use_rag": explicit_use_rag},
                )

                # 4. Emit Dynamic Progress Stage
                if detected_route == "rag" and explicit_use_rag is True:
                    org_label = "سازمان"
                    team_label = "پایگاه دانش"
                    if user_org:
                        org_rec = db.query(OrganizationModel).filter(OrganizationModel.id == user_org).first()
                        if org_rec:
                            org_label = org_rec.name
                    if user_team and user_team != "global":
                        team_rec = db.query(TeamModel).filter(TeamModel.id == user_team).first()
                        if team_rec:
                            team_label = team_rec.name
                    progress_text = f"مسیر مکالمه: پایگاه دانش سازمانی ({org_label} / {team_label}) — استخراج برداری اسناد" if is_fa else f"Routing: Enterprise Knowledge Base ({org_label} / {team_label}) — Vector Extraction"
                elif detected_route == "coding":
                    progress_text = "مسیر مکالمه: تولید، تحلیل و خطایابی کد — هدایت به مدل تخصصی کدنویسی" if is_fa else "Routing: Code Development & Debugging — Routing to Coding Model"
                elif detected_route == "reasoning":
                    progress_text = "مسیر مکالمه: استدلال منطقی و حل مسئله — هدایت به مدل استدلالی CoT" if is_fa else "Routing: Logical Reasoning & Problem Solving — Routing to CoT Model"
                else:
                    progress_text = "مسیر مکالمه: دستیار هوشمند عمومی — پردازش محاوره‌ای پرامپت" if is_fa else "Routing: General Conversational Assistant"

                yield f"event: stage\ndata: {json.dumps({'type': 'stage', 'requestId': req_id, 'stage': 'routing', 'route': detected_route, 'confidence': confidence_score, 'method': routing_method, 'patterns': matched_patterns, 'text': progress_text}, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.02)

                # 5. Federated Vector RAG Retrieval
                real_citations = []
                rag_context_text = ""
                rag_search_latency_ms = 0.0

                if detected_route == "rag" and explicit_use_rag is True:
                    prev_user_queries = [m.get("content", "") for m in messages_list[:-1] if m.get("role") == "user" and m.get("content")]
                    contextual_query = f"{prev_user_queries[-1]} {payload.message}" if prev_user_queries else payload.message

                    search_res = FederatedSearchService.search(
                        query=payload.message,
                        contextual_query=contextual_query,
                        user=user,
                        db=db,
                        has_history=bool(prev_user_queries),
                    )
                    real_citations = search_res["citations"]
                    rag_context_text = search_res["context"]
                    rag_search_latency_ms = search_res["latency_ms"]

                    trace.span(
                        name="vector_rag_retrieval",
                        input_data={
                            "query": payload.message,
                            "shards_queried": [user_org or "global", user_team or "global", "global"],
                            "top_k": 4,
                        },
                        output_data={"citations_count": len(real_citations), "assembled_context": rag_context_text},
                        metadata={"duration_ms": rag_search_latency_ms, "organization_id": user_org, "team_id": user_team},
                    )

                    rag_tool_summary = f"{len(real_citations)} سند معتبر سازمانی" if real_citations else "بدون سند منطبق در پایگاه داده"
                    yield f"event: tool\ndata: {json.dumps({'type': 'tool', 'requestId': req_id, 'name': 'vector_rag', 'label': 'جستجوی برداری اسناد در Weaviate', 'status': 'completed', 'summary': rag_tool_summary}, ensure_ascii=False)}\n\n"

                for cit in real_citations:
                    yield f"event: citation\ndata: {json.dumps(cit, ensure_ascii=False)}\n\n"

                # 6. Active Role Mapping & System Prompt
                # Query actual live models from LiteLLM Proxy, Registry Nodes, and DB
                live_litellm_models = set(litellm_client.get_available_model_names())

                db_active_roles = set()
                try:
                    db_active_roles = {m.assigned_role for m in db.query(ManagedModelModel).filter(ManagedModelModel.is_enabled == True).all()}
                except Exception:
                    pass

                node_active_roles = set()
                try:
                    from app.integrations.registry import registry_client
                    for n in registry_client.get_nodes():
                        if n.get("status") == "healthy":
                            if n.get("served_model_name"):
                                node_active_roles.add(n["served_model_name"])
                            for r in n.get("supported_roles", []):
                                node_active_roles.add(r)
                            node_active_roles.add("general-model")
                except Exception:
                    pass

                # Unified pool of all available roles/models across the entire sovereign stack
                all_active_roles = live_litellm_models.union(db_active_roles).union(node_active_roles)

                target_model = None
                if detected_route == "coding" and "coding-model" in all_active_roles:
                    target_model = "coding-model"
                elif detected_route == "reasoning" and "reasoning-model" in all_active_roles:
                    target_model = "reasoning-model"
                elif detected_route == "rag" and explicit_use_rag is True and "rag-model" in all_active_roles:
                    target_model = "rag-model"
                elif "general-model" in all_active_roles:
                    target_model = "general-model"
                elif "coding-model" in all_active_roles:
                    target_model = "coding-model"
                elif "reasoning-model" in all_active_roles:
                    target_model = "reasoning-model"
                elif live_litellm_models:
                    target_model = next(iter(live_litellm_models))
                elif all_active_roles:
                    target_model = next(iter(all_active_roles))
                else:
                    target_model = "general-model"

                system_prompt = ChatPromptBuilder.build_system_prompt(
                    route=detected_route,
                    explicit_use_rag=bool(explicit_use_rag),
                    rag_context_text=rag_context_text,
                    is_fa=is_fa,
                )

                # 7. LLM Stream Processing with Thinking Delimiters
                t_start_llm = time.time()
                is_connected = False
                stream_parser = StreamBufferParser()

                # Build context window (System prompt + Prior turns + Current prompt)
                reply_snippet = payload.reply_to_snippet or payload.replyToSnippet

                history_turns = []
                for m in messages_list[:-1]:
                    r = m.get("role")
                    c = m.get("content")
                    if r in ("user", "assistant") and c and isinstance(c, str) and c.strip():
                        history_turns.append({"role": r, "content": c.strip()})

                if reply_snippet and isinstance(reply_snippet, str) and reply_snippet.strip():
                    clean_snip = reply_snippet.strip()
                    user_content = (
                        f"[در پاسخ به متن:\n«{clean_snip}»]\n\n{payload.message}"
                        if is_fa else
                        f"[Replying to:\n\"{clean_snip}\"]\n\n{payload.message}"
                    )
                    # When explicitly replying to a snippet, prioritize that snippet and keep at most 2 prior messages
                    if len(history_turns) > 2:
                        history_turns = history_turns[-2:]
                else:
                    user_content = payload.message
                    # Keep a tight, focused history (last 4 messages / 2 back-and-forth turns)
                    if len(history_turns) > 4:
                        history_turns = history_turns[-4:]

                chat_messages = [{"role": "system", "content": system_prompt}] + history_turns + [{"role": "user", "content": user_content}]

                stream_gen = litellm_client.chat_completion_stream(
                    model=target_model,
                    messages=chat_messages,
                    user_id=user.get("id", "u_admin"),
                    metadata={
                        "route": detected_route,
                        "use_rag": explicit_use_rag,
                        "citations_count": len(real_citations),
                        "user_email": user.get("email"),
                        "organization_id": user_org,
                        "team_id": user_team,
                    },
                    max_tokens=2048,
                    temperature=0.7,
                    presence_penalty=0.15,
                    frequency_penalty=0.25,
                )

                async for chunk in stream_gen:
                    choices = chunk.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta") or {}

                    # Dedicated reasoning delta (DeepSeek-R1, OpenAI o1/o3, vLLM CoT)
                    reasoning_chunk = delta.get("reasoning_content") or delta.get("reasoning") or delta.get("thought")
                    if reasoning_chunk:
                        is_connected = True
                        clean_rc = reasoning_chunk.replace("<think>", "").replace("</think>", "")
                        if clean_rc:
                            stream_parser.accumulated_thinking += clean_rc
                            yield f"event: thinking\ndata: {json.dumps({'type': 'thinking', 'requestId': req_id, 'text': clean_rc}, ensure_ascii=False)}\n\n"
                            await asyncio.sleep(0.015)

                    # Real-time stream parsing for embedded <think>...</think> tags
                    content_chunk = delta.get("content")
                    if content_chunk:
                        is_connected = True
                        for ev_type, ev_text in stream_parser.feed(content_chunk):
                            if ev_type == "thinking":
                                yield f"event: thinking\ndata: {json.dumps({'type': 'thinking', 'requestId': req_id, 'text': ev_text}, ensure_ascii=False)}\n\n"
                                await asyncio.sleep(0.015)
                            elif ev_type == "delta":
                                yield f"event: delta\ndata: {json.dumps({'type': 'delta', 'requestId': req_id, 'text': ev_text, 'content': stream_parser.accumulated_answer.strip()}, ensure_ascii=False)}\n\n"
                                await asyncio.sleep(0.025)

                # Fallback to any alternative active model if target_model did not respond
                if not is_connected:
                    fallback_pool = []
                    for cand in (["general-model", "coding-model", "reasoning-model"] + list(live_litellm_models) + list(all_active_roles)):
                        if cand != target_model and cand not in fallback_pool:
                            fallback_pool.append(cand)

                    for alt_model in fallback_pool:
                        if is_connected:
                            break
                        logger.info(f"Target model '{target_model}' stream did not respond; trying alternative model '{alt_model}'...")
                        fb_gen = litellm_client.chat_completion_stream(
                            model=alt_model,
                            messages=chat_messages,
                            user_id=user.get("id", "u_admin"),
                            metadata={
                                "route": detected_route,
                                "fallback_from": target_model,
                                "use_rag": explicit_use_rag,
                                "citations_count": len(real_citations),
                                "user_email": user.get("email"),
                            },
                        )
                        async for chunk in fb_gen:
                            choices = chunk.get("choices") or []
                            if not choices:
                                continue
                            delta = choices[0].get("delta") or {}
                            reasoning_chunk = delta.get("reasoning_content") or delta.get("reasoning") or delta.get("thought")
                            if reasoning_chunk:
                                is_connected = True
                                clean_rc = reasoning_chunk.replace("<think>", "").replace("</think>", "")
                                if clean_rc:
                                    stream_parser.accumulated_thinking += clean_rc
                                    yield f"event: thinking\ndata: {json.dumps({'type': 'thinking', 'requestId': req_id, 'text': clean_rc}, ensure_ascii=False)}\n\n"
                                    await asyncio.sleep(0.015)
                            content_chunk = delta.get("content")
                            if content_chunk:
                                is_connected = True
                                for ev_type, ev_text in stream_parser.feed(content_chunk):
                                    if ev_type == "thinking":
                                        yield f"event: thinking\ndata: {json.dumps({'type': 'thinking', 'requestId': req_id, 'text': ev_text}, ensure_ascii=False)}\n\n"
                                        await asyncio.sleep(0.015)
                                    elif ev_type == "delta":
                                        yield f"event: delta\ndata: {json.dumps({'type': 'delta', 'requestId': req_id, 'text': ev_text, 'content': stream_parser.accumulated_answer.strip()}, ensure_ascii=False)}\n\n"
                                        await asyncio.sleep(0.025)

                # Flush parser buffer
                if is_connected:
                    for ev_type, ev_text in stream_parser.finalize():
                        if ev_type == "thinking":
                            yield f"event: thinking\ndata: {json.dumps({'type': 'thinking', 'requestId': req_id, 'text': ev_text}, ensure_ascii=False)}\n\n"
                            await asyncio.sleep(0.015)
                        elif ev_type == "delta":
                            yield f"event: delta\ndata: {json.dumps({'type': 'delta', 'requestId': req_id, 'text': ev_text, 'content': stream_parser.accumulated_answer.strip()}, ensure_ascii=False)}\n\n"
                            await asyncio.sleep(0.025)

                real_text = stream_parser.accumulated_answer.strip()
                thinking_text = stream_parser.accumulated_thinking.strip()

                # 8. Offline Simulation Fallback
                if not is_connected:
                    async for ev_type, sse_chunk, raw_text in ChatOfflineFallback.stream_simulation(
                        route=detected_route,
                        citations_count=len(real_citations),
                        prompt_snippet=payload.message[:30],
                        is_fa=is_fa,
                        req_id=req_id,
                    ):
                        if ev_type == "thinking":
                            thinking_text += raw_text
                        elif ev_type == "delta":
                            real_text += raw_text
                        yield sse_chunk

                llm_latency_ms = round((time.time() - t_start_llm) * 1000, 2)

                # 9. Sanitize Output and Guarantee Reasoning Section
                clean_final_content = re.sub(r'<think>.*?</think>', '', real_text, flags=re.DOTALL)
                clean_final_content = re.sub(r'</?think>', '', clean_final_content).strip()
                clean_thinking = re.sub(r'</?think>', '', thinking_text).strip()

                if not clean_final_content and clean_thinking:
                    clean_final_content = clean_thinking
                    clean_thinking = ""

                if not clean_thinking:
                    clean_thinking = ChatOfflineFallback.get_offline_thinking(
                        route=detected_route,
                        citations_count=len(real_citations),
                        prompt_snippet=payload.message[:30],
                        is_fa=is_fa,
                    )

                # 10. Estimate Token Consumption
                prompt_tokens_est = max(1, int((len(system_prompt) + len(payload.message)) / 3.2))
                completion_tokens_est = max(1, int((len(clean_final_content) + len(clean_thinking)) / 3.2))
                total_tokens_est = prompt_tokens_est + completion_tokens_est

                trace.generation(
                    name="llm_generation",
                    model=target_model,
                    model_parameters={"temperature": 0.3, "max_tokens": 4096, "top_p": 0.95},
                    input_data=chat_messages,
                    output_data={"content": clean_final_content, "thinking_chain": clean_thinking if clean_thinking else None},
                    usage={"prompt_tokens": prompt_tokens_est, "completion_tokens": completion_tokens_est, "total_tokens": total_tokens_est},
                    metadata={"duration_ms": llm_latency_ms, "cluster_connected": is_connected, "citations_count": len(real_citations)},
                )

                assistant_message_obj = {
                    "id": f"msg_{uuid.uuid4().hex[:8]}",
                    "role": "assistant",
                    "content": clean_final_content,
                    "reasoningContent": clean_thinking if clean_thinking else None,
                    "status": "complete",
                    "citations": real_citations,
                    "createdAt": datetime.now(timezone.utc).isoformat(),
                }
                yield f"event: complete\ndata: {json.dumps({'type': 'complete', 'status': 'complete', 'message': assistant_message_obj}, ensure_ascii=False)}\n\n"

                total_duration_ms = round((time.time() - t_start_request) * 1000, 2)
                trace.update(
                    input_data=payload.message,
                    output_data=real_text.strip(),
                    metadata={
                        "route": detected_route,
                        "routing_method": routing_method,
                        "use_rag": explicit_use_rag,
                        "citations_count": len(real_citations),
                        "cluster_connected": is_connected,
                        "target_model": target_model,
                        "total_duration_ms": total_duration_ms,
                    },
                    tags=[detected_route, "rag" if explicit_use_rag else "no-rag", "connected" if is_connected else "offline_fallback"],
                )

                # 11. Finalize Persistence & Token Accounting
                remaining_tokens = max(0, total_tokens_est - initial_token_deduct)
                ChatConversationManager.finalize_conversation(
                    conv_id=conv_id,
                    assistant_message_obj=assistant_message_obj,
                    remaining_tokens=remaining_tokens,
                    user_id=user_id,
                    user_team=user_team,
                )

            except Exception as unhandled_err:
                logger.error(f"Unhandled error in chat event_generator: {unhandled_err}", exc_info=True)
                trace.record_error("unhandled_stream_error", unhandled_err, input_data=payload.message)
                err_text = "متأسفانه در پردازش درخواست خطایی رخ داد. لطفاً مجدداً تلاش کنید." if is_fa else "An error occurred while processing your request."
                yield f"event: delta\ndata: {json.dumps({'type': 'delta', 'requestId': req_id, 'text': err_text, 'content': err_text}, ensure_ascii=False)}\n\n"
                yield f"event: complete\ndata: {json.dumps({'type': 'complete', 'status': 'failed'}, ensure_ascii=False)}\n\n"
            finally:
                trace.flush()

        return StreamingResponse(event_generator(), media_type="text/event-stream")


chat_service = ChatService()
