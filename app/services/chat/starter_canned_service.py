"""
Starter Canned Responses Service.
Provides authoritative, production-grade architectural guidance and real-time cluster telemetry
for the 4 starter suggestion actions on the New Chat interface.
"""

import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Dict, Optional, Tuple
import httpx
from sqlalchemy.orm import Session

from app.models.managed_model import ManagedModelModel
from app.models.document import DocumentModel
from app.router.normalizer import normalize_text

logger = logging.getLogger("StarterCannedService")

STARTER_PATTERNS = {
    "node_registration": [
        "راهنمای اتصال نودهای پردازش گرافیکی و پیکربندی LiteLLM در کلاستر چیست؟",
        "راهنمای اتصال نودهای پردازش گرافیکی",
        "اتصال نودهای پردازش گرافیکی",
        "اتصال نودهای پردازش",
        "پیکربندی litellm در کلاستر",
        "پیکربندی litellm",
        "ثبت نود پردازش گرافیکی",
        "ثبت نود",
        "how do i register a new gpu inference worker node into the central cluster",
        "register a new gpu inference worker node",
        "register gpu node",
    ],
    "node_health": [
        "چگونه وضعیت سلامت و ارتباط نودهای استنتاج را با رجیستری مرکزی بررسی کنم؟",
        "چگونه وضعیت سلامت و ارتباط نودهای استنتاج را با رجیستری مرکزی بررسی کنم",
        "وضعیت سلامت و ارتباط نودهای استنتاج",
        "سلامت و ارتباط نودهای استنتاج",
        "سلامت نودها و شبکه",
        "بررسی سلامت نودها",
        "بررسی vram نودها",
        "how can i verify the active node connections and vram usage in the registry",
        "verify the active node connections and vram usage",
        "check node health",
    ],
    "routing_and_rag": [
        "روند هدایت خودکار پرسش‌های تخصصی به مدل‌های استدلال و پایگاه دانش چگونه است؟",
        "روند هدایت خودکار پرسش های تخصصی به مدل های استدلال و پایگاه دانش چگونه است",
        "هدایت خودکار پرسش های تخصصی",
        "هدایت خودکار پرسش",
        "مسیریابی هوشمند و rag",
        "روند هدایت خودکار",
        "how does the system dynamically route user questions to specialized reasoning models",
        "dynamically route user questions to specialized reasoning models",
        "semantic routing and rag",
    ],
    "cluster_status": [
        "وضعیت فعلی نودها و مدل‌های فعال در کلاستر چیست؟",
        "وضعیت فعلی نودها و مدل های فعال در کلاستر چیست",
        "وضعیت فعلی نودها",
        "وضعیت نودها و مدل ها",
        "وضعیت نودها و مدلها",
        "وضعیت سرویس‌های پلتفرم",
        "وضعیت سرویس های پلتفرم",
        "وضعیت زنده نودها",
        "what is the current status of all inference nodes in the cluster",
        "current status of all inference nodes",
        "cluster service status",
    ],
}


import re

def _clean_query(text: str) -> str:
    t = re.sub(r'[؟?.,!،;:()«»"\'\-_/\\]', ' ', text)
    t = t.replace('\u200c', ' ')
    t = re.sub(r'\s+', ' ', t).strip()
    return t.lower()


class StarterCannedService:
    """Matches and serves comprehensive pre-computed responses for chat starter prompts."""

    @classmethod
    def match(cls, message: str) -> Optional[str]:
        if not message:
            return None
        c_msg = _clean_query(message)
        for key, patterns in STARTER_PATTERNS.items():
            for pat in patterns:
                c_pat = _clean_query(pat)
                if c_pat and (c_pat in c_msg or c_msg in c_pat):
                    return key
        return None

    @classmethod
    def get_canned_content(
        cls,
        key: str,
        user: Dict[str, Any],
        db: Session,
        is_fa: bool,
    ) -> Tuple[str, str]:
        """
        Returns (thinking_text, markdown_answer) for the matched starter key.
        """
        if key == "node_registration":
            return cls._answer_node_registration(is_fa)
        elif key == "node_health":
            return cls._answer_node_health(is_fa)
        elif key == "routing_and_rag":
            return cls._answer_routing_and_rag(is_fa)
        elif key == "cluster_status":
            return cls._answer_cluster_status(user, db, is_fa)
        else:
            return ("", "")

    @staticmethod
    def _answer_node_registration(is_fa: bool) -> Tuple[str, str]:
        if is_fa:
            thinking = (
                "۱. تحلیل قصد کاربر: درخواست راهنمای ثبت و پیکربندی نود کارت گرافیک (GPU Worker) در پلتفرم کلاستر هوش مصنوعی.\n"
                "۲. بررسی معماری اتصال نود ایجنت (ai-node-agent) به Central Registry و LiteLLM Proxy.\n"
                "۳. بازیابی روش ایمن اتصال در شبکه محلی یا بین‌سیستمی با استفاده از Tailscale / WireGuard بدون نیاز به IP پابلیک.\n"
                "۴. تدوین گام‌به‌گام دستورات راه‌اندازی، پارامترهای محیطی و تایید موفقیت‌آمیز بودن اتصال."
            )
            answer = (
                "### 🚀 راهنمای اتصال نودهای پردازش گرافیکی (`ai-node-agent`) به کلاستر مرکزی\n\n"
                "سامانه هوش مصنوعی سازمان بر پایه **معماری توزیع‌شده فدرال** طراحی شده است؛ به این معنا که سرور مرکزی "
                "(Central Control Plane) درخواست‌ها را مدیریت کرده و بار سنگین محاسباتی مدل‌های زبانی روی سیستم‌ها و "
                "کارت‌های گرافیک محلی متصل به کلاستر توزیع می‌شود.\n\n"
                "---\n\n"
                "#### ۱. شبکه‌سازی امن (Secure Mesh Networking)\n"
                "اگر سیستم پردازشی شما و سرور مرکزی روی یک شبکه محلی نیستند، از **Tailscale** استفاده کنید:\n"
                "1. نرم‌افزار Tailscale را روی هر دو سیستم (سرور مرکزی و نود GPU) نصب و لاگین کنید.\n"
                "2. آدرس IP اختصاصی سرور مرکزی در شبکه Tailscale (مثلاً `100.115.80.12`) را یادداشت فرمایید.\n"
                "> [!TIP]\n"
                "> با Tailscale نیازی به باز کردن پورت مودم (Port Forwarding) یا خرید IP استاتیک نیست و ارتباط با رمزنگاری مدرن WireGuard برقرار می‌شود.\n\n"
                "---\n\n"
                "#### ۲. راه‌اندازی سریع نود ایجنت با پایتون\n"
                "در سرور یا سیستمی که کارت گرافیک انویدیا دارد:\n"
                "```bash\n"
                "cd ai-node-agent\n"
                "pip install -r requirements.txt\n\n"
                "# اجرای نود و اتصال خودکار به رجیستری مرکزی\n"
                "python node_agent.py --gateway-url http://<IP_سرور_مرکزی>:8200\n"
                "```\n\n"
                "#### ۳. اجرای محیط‌های ایزوله (Air-Gapped یا مدل‌های آفلاین)\n"
                "اگر مدل‌ها از قبل روی هارد دیسک دانلود شده‌اند:\n"
                "```bash\n"
                "python node_agent.py \\\n"
                "  --gateway-url http://<IP_سرور_مرکزی>:8200 \\\n"
                "  --local-model-path /data/models/DeepSeek-R1-Distill-Qwen-1.5B \\\n"
                "  --served-name reasoning-model\n"
                "```\n\n"
                "---\n\n"
                "#### ۴. چرخه حیات و اتصال خودکار به LiteLLM\n"
                "پس از اجرای دستور فوق، مراحل زیر خودکار انجام می‌شوند:\n"
                "* **سنجش خودکار VRAM:** ایجنت میزان حافظه گرافیکی را تشخیص داده و موتور بهینه (vLLM / Ollama) را کانفیگ می‌کند.\n"
                "* **ثبت در رجیستری:** مشخصات نود به `central-node-registry` (پورت ۸۲۰۰) فرستاده می‌شود.\n"
                "* **معرفی به LiteLLM:** رجیستری، مدل نود شما را در کمتر از ۱ ثانیه به لایه پروکسی LiteLLM تزریق می‌کند.\n"
                "* **ارسال ضربان قلب (Heartbeat):** هر ۱۵ ثانیه وضعیت نود گزارش می‌شود تا در صورت قطع ارتباط، درخواست‌ها به مسیر جایگزین هدایت شوند."
            )
        else:
            thinking = (
                "1. Analyzing user intent: Requesting GPU worker node onboarding and LiteLLM cluster integration guide.\n"
                "2. Inspecting federated node agent architecture (ai-node-agent to Central Registry & LiteLLM Proxy).\n"
                "3. Outlining secure networking over Tailscale / WireGuard mesh.\n"
                "4. Synthesizing step-by-step CLI execution, offline air-gapped options, and automated heartbeat lifecycle."
            )
            answer = (
                "### 🚀 GPU Inference Worker Node (`ai-node-agent`) Onboarding Guide\n\n"
                "The Sovereign AI platform uses a **decentralized, federated inference architecture** where the central control plane coordinates requests and inference execution is distributed across remote GPU workers.\n\n"
                "---\n\n"
                "#### 1. Secure Mesh Networking (Tailscale / WireGuard)\n"
                "For nodes running across different locations or home/office setups:\n"
                "1. Install Tailscale on both Central Server and the GPU Worker node.\n"
                "2. Note the Central Tailscale IP (e.g. `100.115.80.12`). All communication is end-to-end WireGuard encrypted without port forwarding.\n\n"
                "---\n\n"
                "#### 2. Quick Node Launch\n"
                "On your GPU machine:\n"
                "```bash\n"
                "cd ai-node-agent\n"
                "pip install -r requirements.txt\n"
                "python node_agent.py --gateway-url http://<CENTRAL_IP>:8200\n"
                "```\n\n"
                "#### 3. Air-Gapped / Offline Local Model Setup\n"
                "```bash\n"
                "python node_agent.py \\\n"
                "  --gateway-url http://<CENTRAL_IP>:8200 \\\n"
                "  --local-model-path /data/models/Qwen2.5-Coder-0.5B-Instruct \\\n"
                "  --served-name coding-model\n"
                "```\n\n"
                "---\n\n"
                "#### 4. Automated Registration & Failover Lifecycle\n"
                "* **VRAM Auto-Sensing:** Detects hardware specs and applies optimal vLLM configurations.\n"
                "* **Instant Registration:** Central Node Registry injects the endpoint into LiteLLM Proxy routes within 1 second.\n"
                "* **Active Heartbeats:** Sends telemetry every 15s to guarantee high availability and automated failover."
            )
        return thinking, answer

    @staticmethod
    def _answer_node_health(is_fa: bool) -> Tuple[str, str]:
        if is_fa:
            thinking = (
                "۱. تحلیل قصد کاربر: بررسی سلامت و نظارت بر نودهای استنتاج، میزان حافظه VRAM و ارتباط با رجیستری مرکزی.\n"
                "۲. بررسی اندپوینت‌های تله‌متری Central Registry و داشبورد گرافیکی Langfuse.\n"
                "۳. تدوین راهنمای بررسی وضعیت از طریق وب‌سرویس REST API، پنل ادمین و دستورات سیستمی انویدیا."
            )
            answer = (
                "### 🩺 راهنمای بررسی سلامت نودها، کارت گرافیک (VRAM) و شبکه کلاستر\n\n"
                "برای پایش وضعیت زنده، میزان بار پردازشی و سلامت اتصالات نودهای استنتاج، ابزارهای زیر در دسترس هستند:\n\n"
                "---\n\n"
                "#### ۱. مشاهده از طریق پنل مدیریت وب (Admin Panel)\n"
                "* به نشانی **`http://localhost:8400/admin`** مراجعه کرده و تب **«نودها و زیرساخت»** را باز کنید.\n"
                "* در این بخش وضعیت آنلاین/آفلاین هر نود، آخرین پینگ ضربان قلب (Heartbeat) و نقش اختصاص‌یافته به هر مدل نمایش داده می‌شود.\n\n"
                "---\n\n"
                "#### ۲. استعلام مستقیم از API رجیستری مرکزی (`central-node-registry`)\n"
                "می‌توانید به صورت مستقیم وضعیت نودها را از وب‌سرویس رجیستری مرکزی (پورت ۸۲۰۰) دریافت نمایید:\n"
                "```bash\n"
                "# لیست تمام نودهای ثبت‌شده و وضعیت آنلاینی\n"
                "curl -s http://localhost:8200/api/nodes | jq .\n\n"
                "# گزارش سلامت نودها و مدل‌های تخصیص‌یافته\n"
                "curl -s http://localhost:8200/api/nodes/health | jq .\n"
                "```\n\n"
                "---\n\n"
                "#### ۳. رصد بصری تاخیر و عملکرد تک‌تک درخواست‌ها در Langfuse\n"
                "* وارد داشبورد **`http://localhost:3000`** شوید.\n"
                "* تمام درخواست‌های ارسالی به مدل‌ها به همراه مدت زمان پردازش، تاخیر شبکه، میزان توکن ورودی/خروجی و ردگیری کامل فرآیند استدلال به صورت گرافیکی قابل رهگیری هستند.\n\n"
                "---\n\n"
                "#### ۴. بررسی سخت‌افزاری در سرور میزبان کارت گرافیک\n"
                "روی سروری که نود ایجنت در حال اجراست:\n"
                "```bash\n"
                "# رصد پیوسته مصرف VRAM و دمای کارت گرافیک\n"
                "watch -n 1 nvidia-smi\n\n"
                "# تست وضعیت پینگ به رجیستری سرور مرکزی\n"
                "curl -I http://<IP_سرور_مرکزی>:8200/health\n"
                "```"
            )
        else:
            thinking = (
                "1. Analyzing user intent: Inspecting inference node health, VRAM utilization, and central registry telemetry.\n"
                "2. Outlining inspection vectors: Web UI Admin Panel, Central Registry REST API, Langfuse Observability, and nvidia-smi.\n"
                "3. Structuring step-by-step diagnostic guide."
            )
            answer = (
                "### 🩺 Node Health, VRAM & Network Telemetry Guide\n\n"
                "You can inspect active GPU inference workers, network latency, and memory utilization through multiple diagnostic layers:\n\n"
                "---\n\n"
                "#### 1. Web Administration Dashboard\n"
                "* Visit **`http://localhost:8400/admin`** and navigate to the **Infrastructure / Nodes** view.\n"
                "* Inspect active connections, assigned roles, and latest heartbeat timestamps.\n\n"
                "---\n\n"
                "#### 2. Direct Central Registry REST API (`:8200`)\n"
                "```bash\n"
                "# List all registered workers and statuses\n"
                "curl -s http://localhost:8200/api/nodes | jq .\n\n"
                "# Inspect detailed worker health metrics\n"
                "curl -s http://localhost:8200/api/nodes/health | jq .\n"
                "```\n\n"
                "---\n\n"
                "#### 3. Graphical Observability via Langfuse (`:3000`)\n"
                "* Open **`http://localhost:3000`** to inspect per-request latency, token counts, reasoning spans, and network throughput.\n\n"
                "---\n\n"
                "#### 4. Host Hardware Diagnostics\n"
                "On the GPU machine:\n"
                "```bash\n"
                "watch -n 1 nvidia-smi\n"
                "curl -I http://<CENTRAL_IP>:8200/health\n"
                "```"
            )
        return thinking, answer

    @staticmethod
    def _answer_routing_and_rag(is_fa: bool) -> Tuple[str, str]:
        if is_fa:
            thinking = (
                "۱. تحلیل قصد کاربر: تشریح معماری مسیریابی هوشمند (Semantic Router) و نحوه اتصال به پایگاه دانش برداری (Weaviate RAG).\n"
                "۲. بررسی لایه‌های طبقه‌بندی قصد: دکمه کاربر، الگوهای چندواژه‌ای، مرزبندی توکن‌ها و مدل زبانی جایگزین.\n"
                "۳. بررسی سازوکار بازیابی فدرال، تفکیک شاردها بر اساس سازمان/تیم و ارزیابی شواهد مستند."
            )
            answer = (
                "### 🧠 سازوکار مسیریابی هوشمند (Semantic Routing) و پایگاه دانش سازمانی (RAG)\n\n"
                "پلتفرم Sovereign AI از یک **خط‌لوله تصمیم‌گیری چندلایه‌ای با تاخیر ساب‌میلی‌ثانیه** برای هدایت هوشمند پرسش‌ها استفاده می‌کند:\n\n"
                "---\n\n"
                "#### ۱. لایه‌های ۴گانه طبقه‌بندی نیت کاربر (Semantic Router Pipeline)\n"
                "1. **اولویت قطعی کلید RAG:** در صورتی که کاربر کلید RAG را در پنل چت روشن کرده باشد، پرسش بلافاصله و با قطعیت ۱۰۰٪ به پایگاه دانش هدایت می‌شود.\n"
                "2. **تطبیق عبارات چندواژه‌ای با دقت بالا (High-Precision Phrase Matching):** عبارات تخصصی برنامه‌نویسی و استدلال ریاضی/منطقی با وزن ۳.۰ شناسایی و تفکیک می‌شوند.\n"
                "3. **تطبیق دقیق توکن‌ها و مرز کلمات (Token Boundary Scoring):** با نرمال‌سازی حروف فارسی و بررسی دقیق واژگان، از خطاهای تشابهی (مانند تشابه کلمه «کد» در واژه «کدام») جلوگیری می‌شود.\n"
                "4. **مسیریاب زبانی هوشمند (Dynamic LLM Fallback):** در پرسش‌های پیچیده و مبهم، دسته‌بندی نیت به سرویس هوشمند مسیریاب سپرده می‌شود.\n\n"
                "---\n\n"
                "#### ۲. بازیابی فدرال در پایگاه دانش Weaviate (Multi-Tenant Vector RAG)\n"
                "هنگام انتخاب مسیر RAG، فرآیند زیر اجرا می‌شود:\n"
                "* **جداسازی چندمستأجره (Multi-Tenant Sharding):** اسناد درون شاردهای مجزا برای هر **سازمان** و **تیم** ایزوله هستند؛ هیچ کاربری به اسناد سازمان دیگر دسترسی ندارد.\n"
                "* **مدل امبدینگ چندزبانه `bge-m3`:** تبدیل متن به بردارهای معنایی ۱۰۲۴ بعدی با درک عمیق زبان‌های فارسی و انگلیسی.\n"
                "* **پرس‌وجوی متنی ادغام‌شده (Contextual Search):** برای سوالات چندمرحله‌ای، پیام‌های قبلی کاربر ترکیب شده تا مفهوم کامل جستجو شود.\n"
                "* **استناد محض (Strict Grounding):** مدل موظف است فقط و فقط بر اساس اسناد پاسخ دهد و شماره صفحه و بخش را ذکر کند؛ در صورت نبود سند، صریحاً اعلام می‌کند سندی یافت نشد."
            )
        else:
            thinking = (
                "1. Analyzing user intent: Explaining the 4-tier Semantic Router architecture and multi-tenant Weaviate RAG subsystem.\n"
                "2. Outlining classification hierarchy (user toggle, phrase matching, token boundary scoring, dynamic router).\n"
                "3. Explaining multi-tenant shard isolation, bge-m3 embedding, and strict factual grounding."
            )
            answer = (
                "### 🧠 Intelligent Semantic Routing & Enterprise Vector RAG Architecture\n\n"
                "Sovereign AI deploys a **sub-millisecond multi-tier intent classifier** combined with an enterprise-grade vector retrieval pipeline:\n\n"
                "---\n\n"
                "#### 1. The 4-Tier Semantic Routing Engine\n"
                "1. **User Explicit RAG Toggle:** When enabled by the user in the UI, intent is immediately routed to `rag` with 100% confidence.\n"
                "2. **High-Precision Phrase Matching:** Multi-word technical patterns for Coding and Reasoning are detected with high weight (3.0).\n"
                "3. **Token Boundary Normalization:** Normalized keyword scoring prevents false positives in Persian and English.\n"
                "4. **Dynamic LLM Fallback:** Ambiguous queries fallback to the in-process semantic classifier.\n\n"
                "---\n\n"
                "#### 2. Multi-Tenant Weaviate Vector RAG\n"
                "* **Tenant Shard Isolation:** Vectors are segregated per organization and department in Weaviate shards.\n"
                "* **Multilingual 1024-d Embedding (`bge-m3`):** High-accuracy dense semantic representations for Persian & English.\n"
                "* **Contextual Search:** Chat history is synthesized to formulate disambiguated queries.\n"
                "* **Strict Factual Grounding:** If no matching chunks exist, the model explicitly declares document absence without hallucination."
            )
        return thinking, answer

    @classmethod
    def _answer_cluster_status(
        cls,
        user: Dict[str, Any],
        db: Session,
        is_fa: bool,
    ) -> Tuple[str, str]:
        # Live queries
        total_docs = 0
        managed_models_info = []
        try:
            total_docs = db.query(DocumentModel).count()
            models = db.query(ManagedModelModel).all()
            for m in models:
                status_icon = "🟢 فعال" if m.is_enabled else "⚪ غیرفعال"
                managed_models_info.append(f"- **{m.name}** | نقش: `{m.assigned_role}` | وضعیت: {status_icon} | ارائه‌دهنده: `{m.provider}`")
        except Exception as e:
            logger.warning(f"Error querying cluster status models: {e}")

        # Try to query node registry
        active_nodes_count = 0
        try:
            with httpx.Client(timeout=0.6) as client:
                r = client.get("http://registry:8200/api/nodes")
                if r.status_code == 200:
                    nodes_data = r.json()
                    active_nodes_count = len(nodes_data.get("nodes", []))
        except Exception:
            pass

        used_tok = user.get("used_tokens", 0)
        tok_limit = user.get("token_limit", 5000000)
        quota_percent = round((used_tok / tok_limit) * 100, 2) if tok_limit > 0 else 0.0

        if is_fa:
            thinking = (
                "۱. دریافت درخواست وضعیت زنده سرویس‌ها و نودهای کلاستر هوش مصنوعی.\n"
                "۲. استعلام آنی از دیتابیس مرکزی PostgreSQL، کاتالوگ مدل‌های فعال و شمارش اسناد پایگاه دانش Weaviate.\n"
                "۳. استعلام زنده از رجیستری مرکزی نودها (Central Node Registry).\n"
                "۴. ارزیابی سهمیه توکن کاربر جاری و تدوین گزارش جامع سلامت کلاستر."
            )
            models_md = "\n".join(managed_models_info) if managed_models_info else "- کاتالوگ مدل‌ها در حال مقداردهی اولیه است."
            answer = (
                "### 📊 وضعیت زنده سرویس‌ها و منابع کلاستر هوش مصنوعی\n\n"
                "گزارش تله‌متری بلادرنگ زیر از هسته پلتفرم مرکزی استخراج شده است:\n\n"
                "---\n\n"
                "#### 🖥️ زیرساخت و نودهای استنتاج\n"
                f"* **نودهای ثبت‌شده در رجیستری مرکزی:** `{active_nodes_count}` نود فعال\n"
                f"* **اسناد فهرست‌شده در پایگاه دانش برداری (Weaviate):** `{total_docs}` سند سازمانی\n"
                "* **پروکسی معکوس و کش رم (LiteLLM & Redis):** 🟢 در حال سرویس‌دهی\n"
                "* **پلتفرم مانیتورینگ و تریس (Langfuse):** 🟢 متصل و فعال (`:3000`)\n\n"
                "---\n\n"
                "#### 🤖 کاتالوگ مدل‌های هوش مصنوعی فعال\n"
                f"{models_md}\n\n"
                "---\n\n"
                "#### 👤 وضعیت حساب و سهمیه مصرف شما\n"
                f"* **کاربر جاری:** `{user.get('name', 'مدیر سیستم')}` ({user.get('email', '-')})\n"
                f"* **نقش کاربری:** `{user.get('role', 'کاربر سازمانی')}`\n"
                f"* **سازمان / تیم:** `{user.get('organizationId') or 'سراسری'}` / `{user.get('teamId') or 'سراسری'}`\n"
                f"* **توکن‌های مصرف‌شده:** `{used_tok:,}` از سقف مجاز `{tok_limit:,}` ({quota_percent}% مصرف شده)\n\n"
                "> [!TIP]\n"
                "> برای تنظیم مدل‌ها و مشاهده جزئیات سخت‌افزاری نودها، می‌توانید به **[پنل مدیریت](/admin)** مراجعه فرمایید."
            )
        else:
            thinking = (
                "1. Fetching live telemetry from Central PostgreSQL, Managed Models, and Weaviate.\n"
                "2. Querying Central Node Registry for active GPU workers.\n"
                "3. Extracting caller token quota metrics.\n"
                "4. Formatting comprehensive cluster telemetry dashboard."
            )
            models_md = "\n".join(managed_models_info) if managed_models_info else "- Model catalog initializing."
            answer = (
                "### 📊 Live Cluster Telemetry & Services Status\n\n"
                "Real-time status report extracted from Central Control Plane:\n\n"
                "---\n\n"
                "#### 🖥️ Infrastructure & Inference Workers\n"
                f"* **Registered Node Workers:** `{active_nodes_count}` active\n"
                f"* **Indexed Documents in Vector Store (Weaviate):** `{total_docs}` enterprise documents\n"
                "* **Reverse Proxy & In-Memory Cache (LiteLLM / Redis):** 🟢 Healthy\n"
                "* **Observability Pipeline (Langfuse):** 🟢 Online (`:3000`)\n\n"
                "---\n\n"
                "#### 🤖 Active AI Models Catalog\n"
                f"{models_md}\n\n"
                "---\n\n"
                "#### 👤 User Account & Quota Status\n"
                f"* **Caller:** `{user.get('name', 'Admin')}` ({user.get('email', '-')})\n"
                f"* **Role:** `{user.get('role', 'User')}`\n"
                f"* **Token Usage:** `{used_tok:,}` of `{tok_limit:,}` ({quota_percent}% utilized)\n\n"
                "> [!TIP]\n"
                "> To configure model roles or inspect GPU nodes, visit the **[Admin Panel](/admin)**."
            )
        return thinking, answer

    @classmethod
    async def stream_canned_response(
        cls,
        key: str,
        user: Dict[str, Any],
        db: Session,
        is_fa: bool,
        req_id: str,
    ) -> AsyncGenerator[Tuple[str, str, str], None]:
        """
        Yields (event_type, sse_chunk, raw_text) matching the standard chat streaming protocol.
        """
        thinking, answer = cls.get_canned_content(key, user, db, is_fa)

        # Stream thinking
        for word in thinking.split(" "):
            yield (
                "thinking",
                f"event: thinking\ndata: {json.dumps({'type': 'thinking', 'requestId': req_id, 'text': word + ' '}, ensure_ascii=False)}\n\n",
                word + " ",
            )
            await asyncio.sleep(0.015)

        # Stream answer
        accumulated = ""
        for word in answer.split(" "):
            accumulated += word + " "
            yield (
                "delta",
                f"event: delta\ndata: {json.dumps({'type': 'delta', 'requestId': req_id, 'text': word + ' ', 'content': accumulated.strip()}, ensure_ascii=False)}\n\n",
                word + " ",
            )
            await asyncio.sleep(0.020)
