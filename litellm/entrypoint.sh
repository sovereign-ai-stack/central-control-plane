#!/bin/bash
# ==============================================================================
# LiteLLM Entrypoint - Automatic Master Key Seeding
# هر بار که LiteLLM بالا میاد، اگه master_key در DB نبود خودش seed می‌کنه
# ==============================================================================

set -e

echo "🚀 Starting LiteLLM Proxy..."

# LiteLLM رو در background اجرا کن
litellm --config /app/config.yaml \
        --host 0.0.0.0 \
        --port 4000 \
        --num_workers 1 &

LITELLM_PID=$!

# صبر کن تا LiteLLM کاملاً ready بشه (max 120s)
echo "⏳ Waiting for LiteLLM to be ready..."
for i in $(seq 1 60); do
    if curl -sf http://127.0.0.1:4000/health/readiness > /dev/null 2>&1; then
        echo "✅ LiteLLM is ready after ${i}x2 seconds"
        break
    fi
    if ! kill -0 "$LITELLM_PID" 2>/dev/null; then
        echo "❌ LiteLLM process died unexpectedly"
        exit 1
    fi
    sleep 2
done

# Master Key رو اگه در DB نبود، خودمون seed می‌کنیم
echo "🔑 Checking master key in DB..."
python3 - << 'PYEOF'
import hashlib
import os
import sys

master_key = os.environ.get("LITELLM_MASTER_KEY", "")
database_url = os.environ.get("DATABASE_URL", "")

if not master_key:
    print("⚠️  LITELLM_MASTER_KEY not set, skipping DB seed")
    sys.exit(0)

if not database_url:
    print("⚠️  DATABASE_URL not set, skipping DB seed")
    sys.exit(0)

key_hash = hashlib.sha256(master_key.encode()).hexdigest()
key_display = f"{master_key[:8]}...{master_key[-4:]}"
print(f"   Key: {key_display}  →  Hash: {key_hash[:16]}...")

try:
    import psycopg2
    from urllib.parse import urlparse

    parsed = urlparse(database_url)
    conn = psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        database=parsed.path.lstrip("/"),
        user=parsed.username,
        password=parsed.password,
        connect_timeout=10,
    )
    cur = conn.cursor()

    # بررسی وجود کلید در DB
    cur.execute(
        'SELECT token FROM "LiteLLM_VerificationToken" WHERE token = %s',
        (key_hash,)
    )
    exists = cur.fetchone()

    if not exists:
        cur.execute(
            """
            INSERT INTO "LiteLLM_VerificationToken"
              (token, key_alias, spend, models, aliases, config, created_at, updated_at)
            VALUES
              (%s, %s, 0.0, %s::jsonb, %s::jsonb, %s::jsonb, NOW(), NOW())
            ON CONFLICT (token) DO NOTHING
            """,
            (key_hash, "master-key-auto-seeded", "[]", "{}", "{}")
        )
        conn.commit()
        print(f"✅ Master key seeded into LiteLLM_VerificationToken successfully")
    else:
        print(f"✅ Master key already exists in DB — no action needed")

    cur.close()
    conn.close()

except ImportError:
    print("⚠️  psycopg2 not found, trying pg8000...")
    try:
        import pg8000
        from urllib.parse import urlparse
        parsed = urlparse(database_url)
        conn = pg8000.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            database=parsed.path.lstrip("/"),
            user=parsed.username,
            password=parsed.password,
        )
        cur = conn.cursor()
        cur.execute(
            'SELECT token FROM "LiteLLM_VerificationToken" WHERE token = %s',
            (key_hash,)
        )
        exists = cur.fetchone()
        if not exists:
            cur.execute(
                """
                INSERT INTO "LiteLLM_VerificationToken"
                  (token, key_alias, spend, models, aliases, config, created_at, updated_at)
                VALUES
                  (%s, %s, 0.0, '[]'::jsonb, '{}'::jsonb, '{}'::jsonb, NOW(), NOW())
                ON CONFLICT (token) DO NOTHING
                """,
                (key_hash, "master-key-auto-seeded")
            )
            conn.commit()
            print("✅ Master key seeded via pg8000")
        conn.close()
    except Exception as e2:
        print(f"⚠️  Could not seed via pg8000 either: {e2}")

except Exception as e:
    print(f"⚠️  Could not seed master key automatically: {e}")
    print("   LiteLLM will still start — manual seeding may be required")

PYEOF

echo "🎯 Master key check complete. LiteLLM is serving requests."

# منتظر LiteLLM بمون
wait "$LITELLM_PID"
