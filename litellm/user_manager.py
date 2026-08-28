#!/usr/bin/env python3
"""
Enterprise User, API Key & Rate Limit Management CLI for LiteLLM Proxy.
Enables administrators to:
1. Generate scoped Virtual API Keys with RPM/TPM and budget caps per department.
2. Inspect live token usage and spending per user/organization.
3. List, update, or revoke access keys.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def http_json_request(
    method: str,
    url: str,
    body: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 30,
) -> Tuple[int, Dict[str, Any]]:
    """Safe HTTP JSON request wrapper using Python standard library."""
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


class LiteLLMAdminClient:
    def __init__(self, base_url: str, master_key: str):
        self.base_url = base_url.rstrip("/")
        self.master_key = master_key
        self.headers = {
            "Authorization": f"Bearer {self.master_key}",
            "Content-Type": "application/json",
        }

    def generate_key(
        self,
        user_id: str,
        key_alias: Optional[str] = None,
        rpm_limit: Optional[int] = 60,
        tpm_limit: Optional[int] = 100000,
        max_budget: Optional[float] = None,
        models: Optional[List[str]] = None,
        duration: Optional[str] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """Generate a new virtual API key with enforced rate limits & token budget."""
        url = f"{self.base_url}/key/generate"
        payload = {
            "user_id": user_id,
            "rpm_limit": rpm_limit,
            "tpm_limit": tpm_limit,
        }
        if key_alias:
            payload["key_alias"] = key_alias
        if max_budget is not None:
            payload["max_budget"] = max_budget
        if models:
            payload["models"] = models
        if duration:
            payload["duration"] = duration

        status, resp = http_json_request("POST", url, body=payload, headers=self.headers)
        return status in (200, 201), resp

    def get_key_info(self, key_or_alias: str) -> Tuple[bool, Dict[str, Any]]:
        """Retrieve rate limits, spend, and token metadata for a specific key."""
        url = f"{self.base_url}/key/info?key={key_or_alias}"
        status, resp = http_json_request("GET", url, headers=self.headers)
        return status == 200, resp

    def get_spend_logs(
        self,
        user_id: Optional[str] = None,
        api_key: Optional[str] = None,
        limit: int = 50,
    ) -> Tuple[bool, Dict[str, Any]]:
        """Fetch audit log of prompt/completion tokens and requests."""
        params = [f"limit={limit}"]
        if user_id:
            params.append(f"user_id={user_id}")
        if api_key:
            params.append(f"api_key={api_key}")
        url = f"{self.base_url}/spend/logs?{'&'.join(params)}"
        status, resp = http_json_request("GET", url, headers=self.headers)
        return status == 200, resp

    def delete_key(self, keys: List[str]) -> Tuple[bool, Dict[str, Any]]:
        """Revoke one or more API keys permanently."""
        url = f"{self.base_url}/key/delete"
        payload = {"keys": keys}
        status, resp = http_json_request("POST", url, body=payload, headers=self.headers)
        return status == 200, resp


def main():
    parser = argparse.ArgumentParser(
        description="Enterprise LiteLLM User & Key Manager (Rate Limiting + Token Accounting)"
    )
    parser.add_argument("--url", default=os.environ.get("LITELLM_URL", "http://localhost:4000"), help="LiteLLM URL")
    parser.add_argument("--master-key", default=os.environ.get("LITELLM_MASTER_KEY", "sk-lite-master-1234"), help="Master Admin Key")

    subparsers = parser.add_subparsers(dest="command", required=True, help="Sub-command")

    # Command: create-key
    create_parser = subparsers.add_parser("create-key", help="Create a new scoped organization API Key")
    create_parser.add_argument("--user-id", required=True, help="Organization or Department ID (e.g. finance-dept)")
    create_parser.add_argument("--alias", default=None, help="Human-readable alias (e.g. finance-app-prod)")
    create_parser.add_argument("--rpm", type=int, default=60, help="Requests Per Minute limit (default: 60)")
    create_parser.add_argument("--tpm", type=int, default=100000, help="Tokens Per Minute limit (default: 100,000)")
    create_parser.add_argument("--budget", type=float, default=None, help="Maximum budget / token credit cap")
    create_parser.add_argument("--models", default=None, help="Comma-separated allowed models (default: all)")
    create_parser.add_argument("--duration", default=None, help="Expiration duration (e.g. 30d, 90d)")

    # Command: key-info
    info_parser = subparsers.add_parser("key-info", help="Get metadata and usage for an API Key")
    info_parser.add_argument("--key", required=True, help="API Key or Key Alias to inspect")

    # Command: spend-report
    spend_parser = subparsers.add_parser("spend-report", help="View token usage and spend audit logs")
    spend_parser.add_argument("--user-id", default=None, help="Filter by user/department ID")
    spend_parser.add_argument("--key", default=None, help="Filter by API Key")
    spend_parser.add_argument("--limit", type=int, default=20, help="Number of records to show")

    # Command: revoke-key
    revoke_parser = subparsers.add_parser("revoke-key", help="Revoke/delete an API Key")
    revoke_parser.add_argument("--key", required=True, help="API Key to revoke")

    args = parser.parse_args()
    client = LiteLLMAdminClient(args.url, args.master_key)

    if args.command == "create-key":
        allowed_models = [m.strip() for m in args.models.split(",")] if args.models else None
        ok, res = client.generate_key(
            user_id=args.user_id,
            key_alias=args.alias,
            rpm_limit=args.rpm,
            tpm_limit=args.tpm,
            max_budget=args.budget,
            models=allowed_models,
            duration=args.duration,
        )
        if ok:
            print("\n" + "=" * 65)
            print("  ✅ VIRTUAL API KEY GENERATED SUCCESSFULLY")
            print("=" * 65)
            print(f"  • User / Dept ID : {args.user_id}")
            print(f"  • Key Alias      : {res.get('key_alias') or args.alias or 'N/A'}")
            print(f"  • API Key        : {res.get('key')}")
            print(f"  • Rate Limits    : {args.rpm} RPM | {args.tpm:,} TPM")
            print(f"  • Max Budget     : {args.budget or 'Unlimited'}")
            print(f"  • Allowed Models : {allowed_models or 'All Available Models'}")
            print("=" * 65)
            print("  ⚠️  IMPORTANT: Store this key securely. It cannot be recovered.\n")
            return 0
        else:
            print(f"\n❌ Failed to generate key: {res}")
            return 1

    elif args.command == "key-info":
        ok, res = client.get_key_info(args.key)
        if ok:
            info = res.get("info", res)
            print("\n" + "=" * 65)
            print("  📊 API KEY METADATA & USAGE REPORT")
            print("=" * 65)
            print(f"  • User ID        : {info.get('user_id')}")
            print(f"  • Key Alias      : {info.get('key_alias')}")
            print(f"  • Current Spend  : ${info.get('spend', 0):.4f}")
            print(f"  • Max Budget     : {info.get('max_budget') or 'Unlimited'}")
            print(f"  • RPM Limit      : {info.get('rpm_limit')}")
            print(f"  • TPM Limit      : {info.get('tpm_limit')}")
            print(f"  • Allowed Models : {info.get('models') or 'All'}")
            print(f"  • Created At     : {info.get('created_at') or 'N/A'}")
            print(f"  • Expires At     : {info.get('expires') or 'Never'}")
            print("=" * 65 + "\n")
            return 0
        else:
            print(f"\n❌ Error fetching key info: {res}")
            return 1

    elif args.command == "spend-report":
        ok, res = client.get_spend_logs(user_id=args.user_id, api_key=args.key, limit=args.limit)
        if ok:
            rows = res if isinstance(res, list) else res.get("data", [])
            print("\n" + "=" * 80)
            print(f"  📈 RECENT TOKEN USAGE & AUDIT LOGS (Showing {len(rows)} requests)")
            print("=" * 80)
            print(f"{'Time':<20} | {'Model':<15} | {'Prompt Tokens':<15} | {'Output Tokens':<15} | {'Total'}")
            print("-" * 80)
            total_prompt = 0
            total_completion = 0
            for r in rows:
                p_tok = r.get("prompt_tokens") or 0
                c_tok = r.get("completion_tokens") or 0
                t_tok = r.get("total_tokens") or (p_tok + c_tok)
                total_prompt += p_tok
                total_completion += c_tok
                t_str = str(r.get("startTime") or r.get("created_at") or "")[:19]
                print(f"{t_str:<20} | {str(r.get('model')):<15} | {p_tok:<15} | {c_tok:<15} | {t_tok}")
            print("-" * 80)
            print(f"  TOTALS: Input Tokens: {total_prompt:,} | Output Tokens: {total_completion:,} | Combined: {total_prompt + total_completion:,}")
            print("=" * 80 + "\n")
            return 0
        else:
            print(f"\n❌ Error fetching spend logs: {res}")
            return 1

    elif args.command == "revoke-key":
        ok, res = client.delete_key([args.key])
        if ok:
            print(f"\n✅ Successfully revoked key: {args.key}\n")
            return 0
        else:
            print(f"\n❌ Error revoking key: {res}")
            return 1


if __name__ == "__main__":
    sys.exit(main())
