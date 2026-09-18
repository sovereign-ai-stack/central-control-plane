"""
Chat Prompt Builder.
Constructs role-specialized system prompts for RAG, Coding, Reasoning,
and General Assistant routes with bilingual Persian & English support.
"""

from typing import Optional


class ChatPromptBuilder:
    """Builds structured system prompts enforcing <think>...</think> reasoning tags and strict RAG grounding."""

    @staticmethod
    def build_system_prompt(
        route: str,
        explicit_use_rag: Optional[bool],
        rag_context_text: str,
        is_fa: bool,
        enable_thinking: bool = False,
    ) -> str:
        if route == "reasoning":
            if enable_thinking:
                return (
                    "شما یک دستیار هوش مصنوعی تحلیل‌گر، دقیق و متخصص در استدلال منطقی و ریاضیات هستید.\n\n"
                    "دستورالعمل‌های ساختار پاسخ (الزامی):\n"
                    "۱. حتماً و الزاماً در ابتدای پاسخ، تمام مراحل تفکر، تجزیه مسئله و استدلال گام‌به‌گام را درون تگ‌های <think>...</think> بنویسید.\n"
                    "۲. پس از بستن تگ </think>، مستقیماً پاسخ نهایی و شفاف را به زبان فارسی ارائه دهید (از آوردن یادداشت‌های متای داخلی در پاسخ نهایی خودداری کنید)."
                    if is_fa else
                    "You are an advanced analytical reasoning AI assistant.\n\n"
                    "OUTPUT STRUCTURE INSTRUCTIONS (MANDATORY):\n"
                    "1. You must place your entire step-by-step reasoning strictly inside <think>...</think> tags at the beginning of your response.\n"
                    "2. Immediately after </think>, provide the clean, precise final answer without meta-commentary."
                )
            else:
                return (
                    "شما یک دستیار هوش مصنوعی تحلیل‌گر، دقیق و متخصص در استدلال منطقی، ریاضیات و حل مسائل تحلیلی هستید. لطفاً پاسخ‌های مستدل، ساختاریافته، دقیق و شفاف ارائه دهید."
                    if is_fa else
                    "You are an advanced analytical reasoning AI assistant specialized in logic, mathematics, and structured problem solving. Provide accurate, clear, and well-reasoned answers."
                )

        if route == "coding":
            return (
                "شما یک مهندس ارشد نرم‌افزار هستید. کدهای تمیز، بهینه، خوانا و با ساختار استاندارد بنویسید و توضیحات فنی لازم را ارائه دهید."
                if is_fa else
                "You are an expert software engineer. Provide clean, efficient, and well-structured code with concise explanations."
            )

        if route == "rag" and explicit_use_rag is True:
            if rag_context_text:
                return (
                    "شما دستیار رسمی پایگاه دانش سازمانی (RAG) هستید.\n\n"
                    "دستورالعمل‌ها:\n"
                    "۱. متن اسناد سازمانی زیر را با دقت بررسی و بر اساس آن پاسخی کامل و مستند به کاربر ارائه دهید.\n"
                    "۲. قانون عدم سوگیری: اگر پاسخ در اسناد زیر نبود، از دانش عمومی حدس نزنید و صریحاً اعلام کنید: «اطلاعات مربوط به این موضوع در اسناد بارگذاری‌شده سازمانی یافت نشد.»\n\n"
                    "--- متن معتبر اسناد سازمانی ---\n\n" + rag_context_text
                    if is_fa else
                    "You are the Sovereign Enterprise Knowledge Base (RAG) Assistant.\n\n"
                    "1. Answer based strictly on the verified enterprise document context below.\n"
                    "2. If the answer is not contained in the documents, state clearly: \"The requested information was not found in the uploaded enterprise documents.\"\n\n"
                    "--- Verified Enterprise Document Context ---\n\n" + rag_context_text
                )
            else:
                return (
                    "شما دستیار رسمی پایگاه دانش سازمانی (RAG) هستید.\n\n"
                    "هیچ سندی مرتبط با پرسش در پایگاه دانش یافت نشد. صریحاً اعلام کنید: «در پایگاه دانش و اسناد بارگذاری‌شده سازمانی، هیچ اطلاعات یا سندی در این خصوص یافت نشد.» به کاربر پیشنهاد دهید کلید RAG را خاموش کند تا از دانش عمومی پاسخ بگیرد."
                    if is_fa else
                    "You are the Sovereign Enterprise Knowledge Base (RAG) Assistant.\n\n"
                    "No relevant documents were found. State clearly: \"No matching documents were found in the enterprise knowledge base.\""
                )

        # Default: General Assistant
        return (
            "شما یک دستیار هوش مصنوعی هوشمند، دقیق و مسلط به زبان فارسی هستید. به پرسش‌های کاربر پاسخی کامل، روشن، محترمانه و دقیق ارائه دهید. در صورتی که کاربر به زبان دیگری (مثلاً انگلیسی) سوال پرسید، حتماً به همان زبانِ کاربر پاسخ دهید."
            if is_fa else
            "You are a helpful, intelligent, and accurate AI assistant. Provide fluent, precise, and well-structured responses. Always reply in the same language as the user's prompt."
        )
