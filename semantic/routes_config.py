# ==============================================================================
# Semantic Routing Profiles & Intent Training Datasets
# Multilingual (Persian & English) dataset for fast local classification
# Reference: https://github.com/vllm-project/semantic-router
# ==============================================================================

# 1. General Chitchat & Broad Knowledge (Routes to lightweight model, e.g. qwen-7b)
GENERAL_SAMPLES = [
    "سلام، روزت بخیر",
    "صبح بخیر، حالت چطوره؟",
    "یک جوک کوتاه و بامزه بگو",
    "پایتون چیست و چه کاربردهایی دارد؟",
    "یک ایمیل مودبانه برای تشکر از همکار بنویس",
    "تفاوت هوش مصنوعی و یادگیری ماشین چیست؟",
    "امروز هوا چطوره؟",
    "خلاصه داستان شاهنامه فردوسی چیست؟",
    "Hello, how are you today?",
    "Tell me a brief interesting fact",
    "What is the capital of France?",
    "Write a polite thank you note to my manager",
    "Explain what cloud computing means in simple terms",
]

# 2. Specialist Coding & Engineering (Routes to specialized mid/large model, e.g. qwen-14b/32b)
CODING_SAMPLES = [
    "این تابع پایتون را دیباگ کن و خطایش را بگو",
    "یک الگوریتم بهینه برای جستجوی دودویی در پایتون بنویس",
    "چطور یک کوئری SQL بنویسم که رکورد‌های تکراری را حذف کند؟",
    "یک کلاس در TypeScript برای اتصال به WebSocket پیاده‌سازی کن",
    "این قطعه کد Rust را ریفکتور کن تا بدون پنیک اجرا شود",
    "توابع Asyncio در پایتون چطور کار می‌کنند؟ با مثال کد نشان بده",
    "یک اسکریپت Bash برای بکاپ‌گیری اتوماتیک از دیتابیس بنویس",
    "چطور پروژه جنگو یا نودجی‌اس را روی سرور یا لیارا دپلوی کنم؟",
    "Debug this Python memory leak issue in multiprocessing",
    "Write an optimized recursive quicksort function in C++",
    "Create a Dockerfile for a FastAPI application with multi-stage build",
    "How to index a PostgreSQL table for JSONB query performance?",
    "How do I deploy and scale this container on Kubernetes?",
]

# 3. Specialist Reasoning & Complex Analysis (Routes to flagship model, e.g. qwen-32b/72b)
REASONING_SAMPLES = [
    "اثبات کن که جذر عدد ۲ یک عدد گنگ است",
    "این معادله دیفرانسیل مرتبه دوم را با روش ضرایب نامعین حل کن",
    "تحلیل ریسک سبد سرمایه‌گذاری با مدل مارکوویتز را تشریح کن",
    "محاسبه احتمال شرطی با قضیه بیز برای این مسئله آماری",
    "این زنجیره استدلال منطقی را ارزیابی کن و مغالطه‌های آن را پیدا کن",
    "Prove the Pythagorean theorem using geometric deduction",
    "Solve this optimization linear programming problem with constraints",
    "Perform step-by-step mathematical derivation of backpropagation",
]

# 4. Enterprise RAG & Internal Knowledge (Routes to RAG Pipeline + Context Injection)
RAG_SAMPLES = [
    "سیاست مرخصی استحقاقی و استعلاجی شرکت به چه صورت است؟",
    "ساعت کاری، شناوری و نحوه ثبت اضافه‌کاری در پورتال HR چیست؟",
    "بیمه تکمیلی درمان شامل چه خدماتی است و چطور فاکتور ارسال کنم؟",
    "سقف بودجه مجاز برای هزینه‌های ماموریت و اقامت چقدر است؟",
    "درخواست تعمیر یا ارتقای لپ‌تاپ و تجهیزات IT را از چه طریقی ثبت کنم؟",
    "حقوق و پاداش در چه تاریخی از ماه واریز می‌شود؟",
    "شرایط دورکاری و قوانین کار در منزل برای پرسنل چیست؟",
    "فرایند ارزیابی عملکرد سالانه و افزایش حقوق چگونه تعیین می‌شود؟",
    "پروتکل‌های امنیتی واحد حراست در خصوص همراه داشتن تجهیزات چیست؟",
    "What is the company annual leave and sick leave policy?",
    "How do I submit an expense reimbursement ticket to finance?",
    "What health insurance coverage is provided for employees?",
    "Where is the onboarding handbook for new software engineers?",
]

# Fallback Keywords for Instant Ultra-Fast Hybrid Matching
RAG_KEYWORDS = [
    "مرخصی", "ساعت کاری", "بیمه", "حقوق", "دستمزد", "ماموریت", "سیاست",
    "پورتال", "قوانین", "دورکاری", "اضافه‌کاری", "مزایا", "فیش", "اداری",
    "پرسنل", "کارمند", "استعلاجی", "استحقاقی", "آیین‌نامه", "شرکت", "واحد",
]

CODING_KEYWORDS = [
    "کد", "تابع", "دیباگ", "اشکال‌زدایی", "پایتون", "sql", "الگوریتم",
    "کوئری", "کامپایل", "تایپ‌اسکریپت", "جاوااسکریپت", "کلاس", "متغیر",
    "دپلوی", "دیپلوی", "لیارا", "سرور", "هاست", "کانفیگ", "پروژه",
    "deploy", "dockerfile", "git", "api", "function", "class", "async", "bug",
]

REASONING_KEYWORDS = [
    "اثبات", "معادله", "فرمول", "احتمال", "دیفرانسیل", "استدلال",
    "مشتق", "ماتریس", "منطق", "تحلیل ریاضی", "قضیه", "prove", "derive",
]