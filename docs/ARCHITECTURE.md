# mcp-k8s-agent — Architecture

This document explains **how** the mcp-k8s-agent works and **why** it's designed this way. Read this if you want to understand the system, contribute code, or audit the security model.

---

## Table of Contents

1. [What Problem Does This Solve?](#what-problem-does-this-solve)
2. [File Reference](#file-reference)
3. [Design Principles](#design-principles)
4. [System Overview](#system-overview)
5. [Component Deep Dive](#component-deep-dive)
6. [Safety Model](#safety-model)
7. [Request Lifecycle](#request-lifecycle)
8. [Why Not X?](#why-not-x)

---

## What Problem Does This Solve?

**Problem:** AI assistants are useful for Kubernetes troubleshooting and operations, but giving them direct cluster access is dangerous.

**Solution:** This MCP server acts as a **policy-enforced gateway** between AI assistants and Kubernetes. It:

- Exposes a limited set of operations
- Enforces safety policies in code (not prompts)
- Requires explicit approval for changes
- Sanitizes all output

Think of it as a "read-mostly, write-carefully" API for AI-assisted Kubernetes operations.

---

## File Reference

A quick overview of every Python file in the project:

| File | Purpose | Key Functions |
|------|---------|---------------|
| `server.py` | **MCP entry point.** Registers tools, routes requests, wraps responses with sanitization. | `list_tools()`, `call_tool()`, `_safe_call()` |
| `gate.py` | **Policy engine.** Single source of truth for all allow/deny decisions. Every request passes through here before touching Kubernetes. | `enforce()`, `validate_scope()`, `validate_patch_intent()` |
| `tools_read.py` | **Read operations.** Implements list, get, events, and logs tools. All read-only, no approval needed. | `k8s_list()`, `k8s_get()`, `k8s_list_events()`, `k8s_pod_logs()` |
| `tools_write.py` | **Write operations.** Implements delete and patch tools. All require `approved=true`. | `k8s_delete()`, `k8s_patch()` |
| `sanitize.py` | **Output cleaning.** Redacts secrets, passwords, tokens from output. Truncates long logs. | `sanitize_output()`, `prune_k8s_object()` |
| `k8s_resource.py` | **Kubernetes client helper.** Handles kubeconfig loading and resource discovery. | `load_dynamic_client()`, `get_resource()` |

### File Relationships

```
server.py
    │
    ├── imports gate.py (for GateError)
    ├── imports tools_read.py (k8s_list, k8s_get, k8s_list_events, k8s_pod_logs)
    ├── imports tools_write.py (k8s_delete, k8s_patch)
    └── imports sanitize.py (sanitize_output)

tools_read.py
    ├── imports gate.py (RequestContext, enforce)
    ├── imports sanitize.py (prune_k8s_object)
    └── imports k8s_resource.py (load_dynamic_client, get_resource)

tools_write.py
    ├── imports gate.py (RequestContext, enforce)
    └── imports k8s_resource.py (load_dynamic_client, get_resource)

gate.py
    └── standalone (no internal imports)

sanitize.py
    └── standalone (no internal imports)

k8s_resource.py
    └── imports kubernetes client library only
```

### Adding New Features

| If you want to... | Modify these files |
|-------------------|-------------------|
| Add a new read tool | `tools_read.py` + `server.py` (register tool) |
| Add a new write tool | `tools_write.py` + `server.py` + `gate.py` (add validation) |
| Add a new patch action | `gate.py` (allowlist) + `tools_write.py` (implementation) |
| Block a new resource type | `gate.py` (add to `FORBIDDEN_PLURALS`) |
| Add new redaction patterns | `sanitize.py` (add to `REDACT_PATTERNS`) |

---

## Design Principles

These principles guided every decision. They are **not negotiable**.

### 1. Safety is Enforced in Code, Not Prompts

Prompts can be jailbroken. Code cannot (without changing the code).

```
❌ Bad:  "Please don't access secrets"
✅ Good: if plural == "secrets": raise ForbiddenKind()
```

### 2. Fail Closed

If the system can't determine whether an operation is safe, it blocks it.

```python
# If we don't recognize the action, block it
if action not in PATCH_ACTIONS:
    raise InvalidPatchIntent()
```

### 3. One Tool = One API Call

No tool makes multiple Kubernetes API calls behind the scenes. This makes behavior predictable and auditable.

```
❌ Bad:  "describe" tool that calls GET + LIST events + LIST pods
✅ Good: Separate "get" and "list_events" tools
```

### 4. Intent-Based Mutations

The server never accepts raw patches or YAML. Mutations are expressed as **intents** like "scale to 5" or "update image to X". The server generates the actual patch internally.

```
❌ Bad:  {"patch": {"spec": {"replicas": 5}}}
✅ Good: {"action": "scale", "replicas": 5}
```

### 5. Minimal Response Surface

Write operations return structured summaries, not full objects. This prevents accidental information leakage and keeps responses auditable.

```json
{
  "result": "patched",
  "action": "scale",
  "replicas": 5,
  "explain": "Scaled Deployment default/api to 5 replicas."
}
```

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Claude Desktop                            │
│                    (or any MCP client)                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ MCP Protocol (JSON-RPC over stdio)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         server.py                                │
│                                                                  │
│  • Registers tools with MCP                                     │
│  • Routes requests to handlers                                  │
│  • Wraps all responses with sanitize_output()                   │
│  • Catches errors and returns safe text                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                          gate.py                                 │
│                                                                  │
│  THE SINGLE SOURCE OF TRUTH FOR POLICY                          │
│                                                                  │
│  • Validates namespace is present                               │
│  • Blocks forbidden resources (secrets, configmaps)             │
│  • Blocks bulk operations (selectors)                           │
│  • Requires approval for writes                                 │
│  • Validates patch intents (action, params, bounds)             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────┐              ┌──────────────────────┐
│    tools_read.py     │              │    tools_write.py    │
│                      │              │                      │
│  • k8s_list          │              │  • k8s_delete        │
│  • k8s_get           │              │  • k8s_patch         │
│  • k8s_list_events   │              │                      │
│  • k8s_pod_logs      │              │                      │
└──────────────────────┘              └──────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       k8s_resource.py                            │
│                                                                  │
│  • Loads kubeconfig                                             │
│  • Creates DynamicClient                                        │
│  • Resolves plural names to K8s resources                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Kubernetes API Server                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Deep Dive

### server.py — The Entry Point

**Responsibilities:**
- Register tools with MCP protocol
- Route tool calls to handlers
- Wrap responses with `sanitize_output()`
- Convert exceptions to safe text

**Key Pattern:**
```python
async def _safe_call(coro):
    try:
        return await coro
    except GateError as e:
        return f"BLOCKED: {e}"  # Policy violation → clear message
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"  # Other errors → no stack trace
```

All tool outputs go through `sanitize_output()` before reaching the client.

---

### gate.py — The Policy Engine

**This is the most important file.** Every security decision is made here.

**What it enforces:**

| Rule | Code Location |
|------|---------------|
| Namespace required | `validate_scope()` |
| No secrets/configmaps | `validate_kind()`, `validate_plural()` |
| No selectors/bulk ops | `block_bulk_args()` |
| Approval for writes | `require_approval_if_write()` |
| Valid patch intents | `validate_patch_intent()` |
| Replica bounds (0-100) | `validate_patch_intent()` |

**How to add a new blocked resource:**
```python
FORBIDDEN_PLURALS = {
    "secrets",
    "configmaps",
    "mynewresource",  # Add here
}
```

**How to add a new patch action:**
1. Add to `PATCH_ACTIONS`
2. Add allowed plurals to `PATCH_ALLOWED_PLURALS_BY_ACTION`
3. Add validation in `validate_patch_intent()`
4. Add implementation in `tools_write.py`

---

### tools_read.py — Read Operations

**Functions:**
- `k8s_list(namespace, group, version, plural)` → List all resources
- `k8s_get(namespace, name, group, version, plural)` → Get one resource
- `k8s_list_events(namespace)` → List events
- `k8s_pod_logs(namespace, pod, container?, tail_lines?)` → Get logs

**Pattern:**
```python
async def k8s_list(arguments):
    # 1. Build context
    ctx = RequestContext(tool_name="k8s_list", verb="list", ...)
    
    # 2. Enforce policy (raises GateError if blocked)
    enforce(ctx)
    
    # 3. Call Kubernetes API
    items = resource.get(namespace=namespace).to_dict()
    
    # 4. Prune noisy fields
    items = prune_k8s_object(items)
    
    # 5. Return JSON
    return json.dumps(items)
```

---

### tools_write.py — Write Operations

**Functions:**
- `k8s_delete(namespace, name, group, version, plural, approved)` → Delete one resource
- `k8s_patch(namespace, name, ..., action, ...)` → Intent-based mutation

**The patch function generates patches internally:**

```python
if action == "scale":
    patch = {"spec": {"replicas": replicas}}

elif action == "update_image":
    patch = {
        "spec": {
            "template": {
                "spec": {
                    "containers": [{"name": container, "image": image}]
                }
            }
        }
    }

elif action == "rollout_restart":
    patch = {
        "spec": {
            "template": {
                "metadata": {
                    "annotations": {
                        "kubectl.kubernetes.io/restartedAt": timestamp
                    }
                }
            }
        }
    }
```

**Why generate patches internally?**
- Client can't inject malicious patches
- Every mutation is auditable
- Response can include human-readable explanation

---

### sanitize.py — Output Cleaning

**Two functions:**

**`prune_k8s_object(obj)`** — Structural cleanup for K8s objects
- Removes `managedFields`, `resourceVersion`, `uid` (noisy, non-deterministic)
- Redacts Secret `data` fields (defense in depth)

**`sanitize_output(tool_name, raw)`** — Security redaction for all outputs
- Regex-based redaction: passwords, tokens, API keys, JWTs
- High-entropy string detection (catches base64 secrets)
- Output truncation (max 500 lines)

**Pattern matching:**
```python
REDACT_PATTERNS = [
    (re.compile(r"password\s*=\s*\S+", re.IGNORECASE), "password"),
    (re.compile(r"bearer\s+[a-zA-Z0-9\-_.]+", re.IGNORECASE), "bearer"),
    (re.compile(r"eyJ[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+"), "jwt"),
]
```

---

### k8s_resource.py — Kubernetes Client Helper

**Purpose:** Abstract away Kubernetes client complexity.

**Key function:**
```python
def get_resource(dyn: DynamicClient, api_version: str, plural: str):
    # Try API discovery first
    for resource in dyn.resources.search(api_version=api_version):
        if resource.name == plural:
            return resource
    
    # Fallback to hardcoded mapping
    kind = PLURAL_TO_KIND.get(plural.lower())
    if kind:
        return dyn.resources.get(api_version=api_version, kind=kind)
```

This handles the Kubernetes client v34.1.0+ API changes transparently.

---

## Safety Model

### Threat Model

| Threat | Mitigation |
|--------|------------|
| AI tries to read secrets | `gate.py` blocks by plural/kind |
| AI tries bulk delete | `gate.py` blocks selector arguments |
| AI sends malicious patch | Only intent-based actions accepted |
| Output contains credentials | `sanitize.py` redacts patterns |
| AI makes change without approval | `approved=true` required for writes |
| Prompt injection | Policies are in code, not prompts |

### What We Explicitly Don't Protect Against

- **Compromised kubeconfig** — If your kubeconfig is stolen, attacker has direct access
- **Kubernetes RBAC bypass** — We rely on K8s RBAC; we don't replace it
- **Server code modification** — If attacker can edit `gate.py`, game over

### Defense Layers

```
Layer 1: gate.py        — Blocks forbidden operations
Layer 2: sanitize.py    — Redacts sensitive output  
Layer 3: Kubernetes RBAC — Your cluster's own permissions
Layer 4: kubeconfig     — Which cluster/context is used
```

---

## Request Lifecycle

Here's exactly what happens when Claude asks to "scale api to 5 replicas":

```
1. Claude Desktop sends MCP tool call:
   {
     "tool": "k8s_patch",
     "arguments": {
       "namespace": "default",
       "name": "api",
       "group": "apps",
       "version": "v1",
       "plural": "deployments",
       "action": "scale",
       "replicas": 5,
       "approved": true
     }
   }

2. server.py receives request, calls k8s_patch()

3. tools_write.py builds RequestContext and calls gate.enforce()

4. gate.py checks:
   ✓ Has namespace? Yes ("default")
   ✓ Has name? Yes ("api")
   ✓ Forbidden plural? No ("deployments" is allowed)
   ✓ Approved? Yes
   ✓ Valid action? Yes ("scale" is in PATCH_ACTIONS)
   ✓ Valid plural for action? Yes ("deployments" allowed for scale)
   ✓ Replicas in bounds? Yes (5 is between 0-100)

5. tools_write.py generates patch:
   {"spec": {"replicas": 5}}

6. Kubernetes API receives strategic merge patch

7. tools_write.py returns:
   {
     "result": "patched",
     "action": "scale",
     "replicas": 5,
     "explain": "Scaled Deployment default/api to 5 replicas."
   }

8. server.py runs sanitize_output() on response

9. Claude receives sanitized response
```

---

## Why Not X?

### Why not accept raw YAML/JSON patches?

Raw patches can do anything: delete finalizers, modify RBAC, change service accounts. Intent-based actions limit mutations to known-safe changes.

### Why not support cluster-wide operations?

Blast radius. A bug in cluster-wide operations affects everything. Namespace scoping limits damage.

### Why not auto-approve "safe" operations?

No operation is truly safe without context. Scaling to 100 replicas might be fine in dev, catastrophic in prod. Explicit approval forces human review.

### Why not use Kubernetes admission controllers instead?

Admission controllers work at the K8s API level. This server works at the AI interface level. They solve different problems:
- Admission controller: "Is this request allowed by cluster policy?"
- MCP server: "Should an AI be able to make this request at all?"

### Why block ConfigMaps?

ConfigMaps often contain:
- Database connection strings
- API endpoints
- Feature flags that reveal architecture

They're lower risk than Secrets but still sensitive.

---

## Summary

`mcp-k8s-agent` is a **policy-first MCP server** that:

1. **Exposes limited Kubernetes operations** — Only what's needed, nothing more
2. **Enforces safety in code** — The gate.py file is the single source of truth
3. **Uses intent-based mutations** — No raw patches, only known actions
4. **Sanitizes all output** — Credentials never reach the AI
5. **Requires explicit approval** — Humans stay in the loop

This architecture prioritizes safety and auditability over features. That's intentional.