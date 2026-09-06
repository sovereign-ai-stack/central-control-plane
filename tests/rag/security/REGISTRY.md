# Security Regression Registry

Auto-updated per [regression-policy.md](./regression-policy.md). One row per discovered vulnerability with a permanent test.

| Date | SEC-ID | Summary | Test file | PR | Discovered by |
|------|--------|---------|-----------|-----|---------------|
| — | — | (no entries yet) | — | — | — |

## Template for new entries

```markdown
| YYYY-MM-DD | SEC-XX-NNN | One-line description | tests/security/test_*.py | #PR | review/test/prod |
```

## Pre-registered tests (from spec design)

These were designed proactively; mark **implemented** when test file lands:

| SEC-ID | Status | Test file |
|--------|--------|-----------|
| SEC-CO-001 | planned | test_tenant_isolation.py |
| SEC-CO-002 | planned | test_tenant_isolation.py |
| SEC-DE-001 | planned | test_tenant_isolation.py |
| SEC-FG-001 | green | test_forged_scope.py |
| SEC-FG-002 | green | test_forged_scope.py |
| SEC-FG-003 | green | test_forged_scope.py |
| SEC-AU-001 | green | test_auth_context.py |
| SEC-AU-002 | green | test_auth_context.py |
| SEC-AU-008 | green | test_auth_context.py |
| SEC-API-001 | green | test_auth_context.py |
| SEC-API-002 | green | test_auth_context.py |
| SEC-API-003 | green | test_auth_context.py |
| SEC-API-004 | green | test_auth_context.py |
| SEC-API-005 | green | test_auth_context.py |
| SEC-AU-005 | green | test_auth_context.py (via SEC-API-005) |
| SEC-MD-001 | planned | test_metadata_tampering.py |
| SEC-INJ-001 | green | test_prompt_injection.py |
| SEC-RR-002 | green | test_reranker_scope.py |
| PP-SEC-020–023 | green | test_rag_pipeline_security.py |
| PP-SEC-030–033 | green | test_rag_pipeline_security.py |
| PP-SEC-040–042 | green | test_rag_result_contract.py (unit) |
| PP-SEC-050–052 | green | test_rag_pipeline_security.py |

**Status values**: `planned` → `red` → `green` → `merged`
