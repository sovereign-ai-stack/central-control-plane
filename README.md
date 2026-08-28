# 🏢 Enterprise AI Central Control Plane

هسته متمرکز پلتفرم هوش مصنوعی سازمانی شامل:
* **LiteLLM Proxy:** گیتوی معکوس، احراز هویت با API Keys، شمارش توکن و محدودیت نرخ (Rate Limiting) با دیتابیس PostgreSQL.
* **Redis Cache:** لایه کش فوق‌سریع در رم برای پاسخ‌دهی آنی به سوالات تکراری و مدیریت سریع Rate Limit.
* **Langfuse Tracing Dashboard:** پنل گرافیکی پیشرفته برای رصد و تریس زنده مسیر تمام درخواست‌ها از مبدا تا مقصد.
* **Central Node Registry:** سرویس ثبت خودکار نودها، بررسی سلامت (Heartbeat) و معرفی بلادرنگ مدل‌های جدید به LiteLLM.
* **Semantic Router:** لایه مسیریابی هوشمند و تحلیل قصد پرسش کاربران (تشخیص سوالات عمومی، تخصصی یا نیازمند RAG).
* **Web UI:** رابط کاربری چت سازمانی.

---

## 🚀 راهنمای راه‌اندازی سریع

### ۱. بالا آوردن تمام سرویس‌ها با داکر کامپوز:
```bash
cd central-control-plane
docker compose up -d --build
```

### ۲. پورت‌های پنل‌ها و داشبوردها در مرورگر:
* **📊 داشبورد گرافیکی تریس و مسیر درخواست‌ها (Langfuse):** `http://localhost:3000`
* **🛡️ داشبورد مدیریت و صدور کلیدهای API (LiteLLM UI):** `http://localhost:4000/ui`
* **💬 رابط کاربری چت سازمانی (Chat UI):** `http://localhost:8400`
* **⚙️ وب‌سرویس رجیستری مرکزی (Node Registry):** `http://localhost:8200/docs`
* **🧠 وب‌سرویس مسیریاب سمنتیک (Semantic Router):** `http://localhost:8300/docs`
