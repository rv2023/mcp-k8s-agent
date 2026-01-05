# mcp-k8s-agent

`mcp-k8s-agent` is a **safe, deterministic MCP (Model Context Protocol) server** that exposes **strictly limited Kubernetes capabilities** to AI clients.

It is designed for **production-grade safety**, not demos.

---

## What This Is

- An MCP stdio server
- A controlled Kubernetes access layer
- A policy-enforced safety boundary between AI and clusters

---

## What This Is NOT

- ❌ A kubectl replacement
- ❌ A cluster admin agent
- ❌ A free-form AI operator
- ❌ A prompt-driven permission system

---

## Key Guarantees (Phase 3)

### Safety Guarantees
- Secrets are never returned
- Tokens and credentials are redacted
- Logs are bounded and sanitized
- Mutations require explicit approval
- All operations are namespaced
- No cluster-wide access
- No bulk operations

### Determinism Guarantees
- Same input → same output
- No LLM-side sanitization
- No hidden heuristics
- No client-controlled bypasses

---

## Supported Tools

### Read-Only
- `k8s_list`
- `k8s_get`
- `k8s_list_events`
- `k8s_pod_logs`

### Write (Restricted)
- `k8s_delete`
  - Single resource only
  - `approved=true` required

---

## How Safety Is Enforced

1. **Gate** validates intent and scope
2. **Tools** execute minimal Kubernetes calls
3. **Sanitizer** removes sensitive data
4. **MCP server** returns safe output

Safety is enforced **in code**, not prompts.

---

## Running the Server

```bash
python server.py
````

Startup message:

```
mcp-k8s-agent started | Phase 3 enabled | sanitized outputs, bounded logs, approval-gated writes
```

The server communicates exclusively over **stdio**, per MCP spec.

---

## Testing

### Sanitization Tests

```bash
PYTHONPATH=. python tests/test_sanitize.py
```

### MCP Smoke Test

```bash
python tests/smoke_mcp_client.py
```

---

## Design Principles

* Fail closed
* Least privilege
* Explicit approval for risk
* No hidden magic
* Auditability first

---

## Roadmap (High-Level)

* Phase 4: Output classification
* Phase 5: Policy-driven field allowlists
* Phase 6: Optional LLM integration (never raw data)

---

## License

MIT

```

---

## ✅ What Changed (Summary)

- Removed all outdated Phase 1 / Phase 2 references
- Aligned docs to **actual runtime behavior**
- Made sanitization a **first-class architectural layer**
- Explicitly documented **what is refused forever**
- Matched MCP stdio lifecycle and tests

---

### If you want next:
- 🔒 Phase 3 invariants added as code comments
- 🧪 One end-to-end MCP sanitization test
- 🏷️ Phase 3 release tagging
- 🔍 Security gap review

Just tell me the next move.
```
