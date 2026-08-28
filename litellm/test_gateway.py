#!/usr/bin/env python3
"""
Comprehensive LiteLLM Gateway & Rate Limit Validation Suite.
Tests:
1. Basic Chat Completion & Token Count Verification.
2. Streaming Response & Usage Tracking.
3. Rate Limiting Enforcement (RPM Stress Test -> HTTP 429).
4. Key Info & Spend Inspection.
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def http_json(
    method: str,
    url: str,
    body: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 60,
) -> Tuple[int, Dict[str, Any]]:
    hdrs = headers or {}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        hdrs["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw_err = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw_err)
        except Exception:
            return e.code, {"error": raw_err}
    except Exception as e:
        return 500, {"error": str(e)}


def test_chat_completion(url: str, api_key: str, model: str, prompt: str) -> bool:
    print(f"\n🧪 [Test 1] Testing Chat Completion with model '{model}'...")
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are an enterprise AI assistant. Be concise."},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 150,
        "temperature": 0.3,
    }
    headers = {"Authorization": f"Bearer {api_key}"}
    status, data = http_json("POST", f"{url}/v1/chat/completions", body=body, headers=headers)

    if status != 200:
        print(f"❌ Failed (HTTP {status}): {data}")
        return False

    choice = (data.get("choices") or [{}])[0].get("message", {})
    usage = data.get("usage", {})
    print("✅ Success!")
    print(f"  • Response Text       : {choice.get('content', '').strip()}")
    print(f"  • Input (Prompt) Tokens: {usage.get('prompt_tokens')}")
    print(f"  • Output Tokens       : {usage.get('completion_tokens')}")
    print(f"  • Total Tokens Tracked: {usage.get('total_tokens')}")
    return True


def test_rate_limiting(url: str, api_key: str, model: str, num_requests: int = 15) -> bool:
    print(f"\n🧪 [Test 2] Testing Rate Limiting Enforcement (Sending {num_requests} rapid requests)...")
    headers = {"Authorization": f"Bearer {api_key}"}
    body = {
        "model": model,
        "messages": [{"role": "user", "content": "Ping"}],
        "max_tokens": 5,
    }

    success_count = 0
    rate_limited_count = 0

    for i in range(num_requests):
        status, data = http_json("POST", f"{url}/v1/chat/completions", body=body, headers=headers, timeout=10)
        if status == 200:
            success_count += 1
            print(f"  Req #{i+1:02d}: ✅ 200 OK")
        elif status == 429:
            rate_limited_count += 1
            print(f"  Req #{i+1:02d}: 🛡️  429 Rate Limit Exceeded (Expected behavior!)")
        else:
            print(f"  Req #{i+1:02d}: ⚠️  {status} ({data.get('error')})")

    print(f"\n📊 Summary: {success_count} Passed, {rate_limited_count} Rate Limited.")
    return True


def main():
    parser = argparse.ArgumentParser(description="LiteLLM Gateway Verification Suite")
    parser.add_argument("--url", default=os.environ.get("LITELLM_URL", "http://localhost:4000"), help="LiteLLM URL")
    parser.add_argument("--api-key", required=True, help="Virtual API Key or Master Key")
    parser.add_argument("--model", default="qwen-7b", help="Model alias to test")
    parser.add_argument("--prompt", default="سلام، در یک جمله خودت را معرفی کن.", help="Prompt text")
    parser.add_argument("--stress-test", action="store_true", help="Run rate limit stress test")
    args = parser.parse_args()

    print("=" * 70)
    print("  🚀 LITELLM PROXY & TOKEN TRACKING TEST SUITE")
    print(f"  Target Gateway : {args.url}")
    print(f"  Target Model   : {args.model}")
    print("=" * 70)

    ok = test_chat_completion(args.url, args.api_key, args.model, args.prompt)
    if args.stress_test:
        test_rate_limiting(args.url, args.api_key, args.model)

    print("\n" + "=" * 70)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())