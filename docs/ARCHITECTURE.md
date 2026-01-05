Got it. I’ll **replace both files cleanly**, aligned to the **actual Phase 3 code truth**, with **no legacy Phase 1/2 confusion**, no assumptions, and no fluff.

Below are **copy-paste ready replacements**.

---

# ✅ UPDATED `docs/ARCHITECTURE.md`

```md
# Architecture — mcp-k8s-agent (Phase 3)

## Overview

`mcp-k8s-agent` is a **Model Context Protocol (MCP) stdio server** that exposes a **strictly controlled subset of Kubernetes operations** to AI clients.

The system is intentionally designed to be:

- Deterministic
- Auditable
- Fail-closed
- Safe-by-construction

**All safety guarantees are enforced in code, not prompts.**

---

## High-Level Flow

```

MCP Client
|
|  JSON-RPC (stdio)
v
MCP Server (server.py)
|
|  tool dispatch
v
Gate (gate.py)
|
|  allow / block
v
Tool Implementation (tools_read.py / tools_write.py)
|
|  raw Kubernetes data
v
Sanitization Layer (sanitize.py)
|
|  redacted + bounded output
v
MCP Response → Client

```

---

## Core Components

### 1. MCP Server (`server.py`)

Responsibilities:
- MCP protocol handling
- Tool registration
- Request dispatch
- Error normalization
- Startup lifecycle

Non-responsibilities:
- No Kubernetes logic
- No policy decisions
- No sanitization logic

---

### 2. Gate (`gate.py`) — **Single Source of Truth**

The Gate enforces **all policy decisions**.

It validates every request using a `RequestContext`.

#### Enforced guarantees:
- No cluster-wide operations
- No bulk operations
- No selectors
- No Secrets or ConfigMaps
- No writes without `approved=true`
- Namespace must always be explicit
- One tool = one Kubernetes API call

If a request violates policy:
- A `GateError` is raised
- The server converts it to a safe text response
- The server does **not** crash

---

### 3. Tool Layer

#### Read Tools (`tools_read.py`)
- `k8s_list`
- `k8s_get`
- `k8s_list_events`
- `k8s_pod_logs`

Characteristics:
- Namespaced only
- Dynamic discovery for CRDs
- No node-level or host access
- No cloud-provider access

#### Write Tools (`tools_write.py`)
- `k8s_delete` only

Characteristics:
- Single-object deletion
- Explicit name required
- `approved=true` mandatory
- No bulk deletes
- No selectors

---

### 4. Sanitization Layer (`sanitize.py`) — Phase 3

All tool output **must pass through sanitization** before being returned.

#### Sanitization guarantees:
- Secrets are never returned
- Tokens, passwords, API keys are redacted
- JWTs and bearer tokens are removed
- High-entropy strings are redacted
- Log output is size-bounded
- Output is deterministic

Sanitization happens:
- **After** tool execution
- **Before** MCP response
- **Locally**, never in the LLM

---

## What Is Never Exposed

This server will **never** return:

- Kubernetes Secrets
- ConfigMaps
- Secret references
- ServiceAccount tokens
- Node logs
- Host filesystem data
- Cloud provider metadata
- Unbounded logs
- Raw credentials of any form

These are **hard guarantees**, not configuration options.

---

## Threat Model (Explicit)

### Defended Against
- Prompt injection
- Accidental secret leakage
- Over-broad AI queries
- Unsafe mutations
- Log-based credential exposure

### Not In Scope
- RBAC misconfiguration
- Kubernetes cluster compromise
- Malicious kubeconfigs
- Host-level attacks

---

## Design Philosophy

- Safety > intelligence
- Determinism > convenience
- Code enforcement > prompt discipline
- Fewer features, stronger guarantees

Phase 3 completes the **information safety boundary** of the system.
```