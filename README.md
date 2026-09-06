# 🏢 پلتفرم مرکزی هوش مصنوعی سازمانی (Sovereign AI Central Control Plane)
## راهنمای جامع استقرار در محیط عملیاتی (Production Deployment Guide)

این مستند راهنمای گام‌به‌گام و فنی جهت استقرار، شبکه‌سازی امن، تنظیم متغیرهای محیطی، داکر کامپوز و پایش سرور مرکزی در محیط پروداکشن است.

---

### ۱. معماری سرویس‌های مرکزی کلاستر

هسته مرکزی پلتفرم از ۷ ماژول هماهنگ تشکیل شده است:
1. **AI Gateway API (FastAPI + Weaviate RAG):** درگاه اصلی پردازش، احراز هویت سازمانی، مدیریت سهمیه‌ها و موتور جستجوی برداری درون‌پروسسی چندمستأجره.
2. **Next.js Enterprise Web UI:** رابط کاربری مدرن گفتگوی سازمانی با تفکر زنده مدل، استناد به اسناد و پنل مدیریت ادمین.
3. **LiteLLM Reverse Proxy:** توزیع بار، ترجمه فرمت پرامپت‌ها و مسیریابی به نودهای استنتاج توزیع‌شده.
4. **PostgreSQL Database:** ذخیره‌سازی پایدار کاربران، سازمان‌ها، لاگ مکالمات، سهمیه‌ها و فراداده اسناد.
5. **Redis Cache:** کش رم با سرعت ساب‌میلی‌ثانیه برای نرخ‌گذاری درخواست‌ها (Rate Limiting) و کش پاسخ‌ها.
6. **Central Node Registry:** سرویس کشف و ثبت خودکار نودهای محلی GPU و پایش پیوسته ضربان قلب (Heartbeat).
7. **Langfuse Observability:** پنل مانیتورینگ و رهگیری تریس (Tracing) تک‌تک استدلال‌ها و تاخیر درخواست‌ها.

---

### ۲. شبکه‌سازی امن بین سرور و نودها با Tailscale / WireGuard (حیاتی)

برای اینکه نودهای پردازشی (GPU Worker) مستقر در شرکت، منزل یا شعبات بدون نیاز به IP استاتیک، بدون پورت‌فورواردینگ مودم و با امنیت کامل به سرور مرکزی متصل شوند:

#### گام ۱: نصب و لاگین Tailscale روی سرور مرکزی
```bash
# نصب روی سرور لینوکس (اوبونتو/دبیان)
curl -fsSL https://tailscale.com/install.sh | sh

# راه‌اندازی و اتصال به اکانت Tailscale
sudo tailscale up
```

#### گام ۲: دریافت IP اختصاصی سرور در شبکه امن
```bash
tailscale ip -4
# خروجی یک آی‌پی پایدار است، مثلاً: 100.115.80.12
```

#### گام ۳: اشتراک‌گذاری با نودهای گرافیکی
تمام نودهای پردازشی (`ai-node-agent`) که به همین شبکه متصل شوند، می‌توانند با آدرس `http://100.115.80.12:8200` و بدون واسطه با رجیستری مرکزی گفتگو کنند. تمام ارتباطات با پروتکل استاندارد **WireGuard** رمزنگاری می‌شوند.

---

### ۳. تنظیم متغیرهای محیطی پروداکشن (`.env`)

یک فایل با نام `.env` در پوشه `central-control-plane` بسازید:

```ini
# ==========================================
# پایگاه داده PostgreSQL
# ==========================================
POSTGRES_USER=litellm
POSTGRES_PASSWORD=YOUR_STRONG_POSTGRES_PASSWORD_HERE
POSTGRES_DB=litellm
DATABASE_URL=postgresql://litellm:YOUR_STRONG_POSTGRES_PASSWORD_HERE@postgres:5432/litellm

# ==========================================
# لایه پروکسی و مدیریت هوش مصنوعی (LiteLLM)
# ==========================================
LITELLM_MASTER_KEY=sk-prod-super-master-key-change-this
LITELLM_PORT=4000
LITELLM_LOG=WARNING

# ==========================================
# تنظیمات رجیستری و نودها
# ==========================================
REGISTRY_PORT=8200
NODE_TIMEOUT_SECONDS=60

# ==========================================
# پایگاه برداری سازمانی (Weaviate Vector DB)
# ==========================================
RAG_VECTOR_STORE_BACKEND=weaviate
RAG_WEAVIATE_URL=http://weaviate:8080
RAG_WEAVIATE_GRPC_PORT=50051
TRANSFORMERS_OFFLINE=1
INGESTION_WORKERS=4

# ==========================================
# پلتفرم مانیتورینگ و رهگیری (Langfuse)
# ==========================================
LANGFUSE_PUBLIC_KEY=pk-lf-8054958d-e8f3-4661-912c-69a351a5156d
LANGFUSE_SECRET_KEY=sk-lf-468e625d-5c34-45c6-aca2-a0b24877b3f2
LANGFUSE_HOST=http://langfuse:3000
LANGFUSE_ENABLED=true

# ==========================================
# کلید رمزنگاری جلسات و احراز هویت
# ==========================================
APP_SECRET_PATH=
PORT=8000
UI_PORT=8400
```

---

### ۴. راه‌اندازی و مدیریت کلاستر با Docker Compose

#### ۱. اجرای کامل سرویس‌ها:
```bash
docker compose up -d
```

#### ۲. بررسی وضعیت سلامت کانتینرها:
```bash
docker compose ps
```
> تمام کانتینرها باید وضعیت `Up (healthy)` یا `Up` داشته باشند.

#### ۳. مشاهده لاگ‌های زنده:
```bash
# لاگ‌های گیتوی مرکزی و RAG
docker compose logs -f gateway

# لاگ‌های رجیستری و پایش نودها
docker compose logs -f registry
```

---

### ۵. تنظیم Reverse Proxy (Nginx) با پشتیبانی استریم و SSL

در محیط پروداکشن، برای دامنه سازمان و فعال‌سازی SSL (HTTPS)، از کانفیگ Nginx زیر استفاده نمایید.

> [!IMPORTANT]
> حتماً `proxy_buffering off;` را قرار دهید تا پاسخ‌های استریم (SSE) بدون مکث و بلادرنگ برای کاربر ارسال شوند.

```nginx
server {
    listen 80;
    server_name ai.yourdomain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ai.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/ai.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ai.yourdomain.com/privkey.pem;

    # ۱. رابط کاربری وب (Next.js)
    location / {
        proxy_pass http://127.0.0.1:8400;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # ۲. درگاه API و استریمینگ SSE چت
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # حیاتی برای استریمینگ آنی هوش مصنوعی:
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
        proxy_set_header Connection '';
        chunked_transfer_encoding on;
    }
}
```

---

### ۶. راهبرد پشتیبان‌گیری منظم (Backup Strategy)

* **پشتیبان‌گیری از دیتابیس کاربران، چت‌ها و متاداده:**
  ```bash
  docker exec -t enterprise-postgres pg_dumpall -c -U litellm > /backups/postgres_$(date +%Y%m%d).sql
  ```
* **پشتیبان‌گیری از بردارها و شاردهای پایگاه دانش Weaviate:**
  مسیر ولوم داکر `central-control-plane_weaviate-data` را در پشتیبان‌گیری دوره‌ای فایل‌های سرور قرار دهید.
