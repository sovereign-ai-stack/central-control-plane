"""
Chat Offline Fallback Simulator.
Provides graceful, structured reasoning chains and informative status messages
when local GPU worker nodes or LiteLLM Proxy are temporarily unavailable.
"""

import asyncio
import json
from typing import AsyncGenerator, Dict, List, Tuple


class ChatOfflineFallback:
    """Generates simulated reasoning steps and fallback text for disconnected clusters."""

    @staticmethod
    def get_offline_thinking(
        route: str,
        citations_count: int,
        prompt_snippet: str,
        is_fa: bool,
    ) -> str:
        if route == "rag":
            return (
                f"۱. بررسی قصد کاربر: درخواست مبتنی بر بازیابی اسناد پایگاه دانش (مسیر {route}).\n"
                f"۲. جستجوی فدرال در شارد سازمانی: تعداد {citations_count} بخش معتبر بازیابی شد.\n"
                f"۳. بررسی شواهد و انطباق با اسناد سازمانی.\n"
                f"۴. آماده‌سازی ارجاعات و تدوین پاسخ مستند."
                if is_fa else
                f"1. Intent Analysis: RAG retrieval query detected (route: {route}).\n"
                f"2. Federated search: {citations_count} citations matched.\n"
                f"3. Verifying document grounding and factual constraints.\n"
                f"4. Assembling citation cards and final response."
            )
        elif route == "coding":
            return (
                "۱. تحلیل پرسش برنامه‌نویسی و استخراج نیازمندی‌های الگوریتمی.\n"
                "۲. بررسی بهینه‌سازی حافظه و پیچیدگی زمانی.\n"
                "۳. انتخاب بهترین الگو و ساختار داده.\n"
                "۴. نگارش کد استاندارد و توضیحات فنی."
                if is_fa else
                "1. Analyzing coding requirements and syntax specifications.\n"
                "2. Evaluating time/space complexity and edge cases.\n"
                "3. Selecting optimal design pattern.\n"
                "4. Generating clean code structure."
            )
        elif route == "reasoning":
            return (
                "۱. تجزیه مسئله به گزاره‌های منطقی اولیه.\n"
                "۲. بررسی فرضیات و استنتاج گام‌به‌گام.\n"
                "۳. اعتبارسنجی فرضیات و استنتاج برهان خلف.\n"
                "۴. نتیجه‌گیری قطعی و تدوین فرمول نهایی."
                if is_fa else
                "1. Decomposing problem into logical premises.\n"
                "2. Step-by-step analytical deduction.\n"
                "3. Validating constraints and logical coherence.\n"
                "4. Deriving final conclusion."
            )
        else:
            return (
                f"۱. دریافت و نرمال‌سازی پرامپت کاربر ({prompt_snippet}...). \n"
                "۲. تشخیص مسیر مکالمه عمومی و هدایت به مدل زبانی.\n"
                "۳. بررسی زمینه گفتگو و تدوین پاسخ جامع."
                if is_fa else
                "1. Normalizing user prompt and intent.\n"
                "2. Routing to general assistant model.\n"
                "3. Synthesizing context and formulating answer."
            )

    @staticmethod
    def get_offline_text(has_citations: bool, is_fa: bool, route: str = "general") -> str:
        if route == "rag" and not has_citations:
            return (
                "در پایگاه دانش و اسناد بارگذاری‌شده سازمانی، هیچ سندی منطبق با پرسش شما یافت نشد.\n\n"
                "💡 اگر مایل به دریافت پاسخ بر اساس دانش عمومی هوش مصنوعی هستید، لطفاً کلید RAG را غیرفعال فرمایید."
                if is_fa else
                "No matching documents were found in the enterprise knowledge base for your query.\n\n"
                "💡 If you wish to receive a general AI answer, please turn off the RAG toggle."
            )
        if has_citations:
            return (
                "📚 **اسناد مرتبط در پایگاه دانش سازمانی (RAG) یافت و استخراج شدند:**\n\n"
                "اطلاعات مورد نظر شما از اسناد سازمانی استخراج گردید (به بخش **«منابع ارجاع داده شده»** در ستون سمت چپ مراجعه فرمایید).\n\n"
                "---\n\n"
                "⚠️ **وضعیت کلاستر هوش مصنوعی:** ارتباط با موتور استنتاج مدل زبانی محلی (LiteLLM یا کارت گرافیک) برقرار نشد."
                if is_fa else
                "📚 **Relevant documents found in enterprise knowledge base.** (See cited sources in left panel)\n\n---\n\n"
                "⚠️ **Cluster Status:** Unable to establish communication with local LLM inference engine."
            )
        else:
            return (
                "سلام و درود! درخواست شما دریافت گردید. برای دریافت پاسخ زنده و نگارش متن از مدل زبانی هوش مصنوعی، لطفاً اطمینان حاصل کنید نود کارت گرافیک (ai-node-agent) یا کانتینر LiteLLM فعال است."
                if is_fa else
                "Hello! Your request was received. To generate live text responses from local LLM, ensure ai-node-agent or litellm is running."
            )

    @classmethod
    async def stream_simulation(
        cls,
        route: str,
        citations_count: int,
        prompt_snippet: str,
        is_fa: bool,
        req_id: str,
    ) -> AsyncGenerator[Tuple[str, str, str], None]:
        """
        Yields (event_type, sse_chunk, raw_text) for offline mode.
        """
        thinking = cls.get_offline_thinking(route, citations_count, prompt_snippet, is_fa)
        for word in thinking.split(" "):
            yield (
                "thinking",
                f"event: thinking\ndata: {json.dumps({'type': 'thinking', 'requestId': req_id, 'text': word + ' '}, ensure_ascii=False)}\n\n",
                word + " ",
            )
            await asyncio.sleep(0.015)

        text = cls.get_offline_text(citations_count > 0, is_fa, route=route)
        accumulated = ""
        for word in text.split(" "):
            accumulated += word + " "
            yield (
                "delta",
                f"event: delta\ndata: {json.dumps({'type': 'delta', 'requestId': req_id, 'text': word + ' ', 'content': accumulated.strip()}, ensure_ascii=False)}\n\n",
                word + " ",
            )
            await asyncio.sleep(0.025)
