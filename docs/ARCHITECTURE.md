# mcp-k8s-agent — Architecture

This document describes the **actual, authoritative architecture** of the `mcp-k8s-agent` as implemented in the current codebase.  
It focuses on components, safety rules, enforcement boundaries, and design guarantees.

---

## 🧠 Overview

`mcp-k8s-agent` is a **Model Context Protocol (MCP) server** that safely exposes a limited set of Kubernetes capabilities to MCP clients over a JSON-RPC/stdio transport.  
The server allows **namespaced reads and controlled deletes** while enforcing strict safety policies in code.

MCP is a standard protocol that defines how clients (e.g., AI agents like Claude Desktop) interact with servers that expose *tools* that perform actions or retrieve contextual data. MCP uses JSON-RPC 2.0 over stdio in this project. :contentReference[oaicite:0]{index=0}

---

## 🛠️ Core Components

### 🧩 Transport

- The MCP server runs an **stdio JSON-RPC transport**.
- Clients connect via standard input/output streams.
- MCP clients must perform the **initialize** handshake before invoking tools.

### 🧠 Protocol Handler

- `server.py` sets up MCP tool discovery and call dispatch.
- It maps tool names (like `k8s_list`, `k8s_get`, `k8s_delete`) to handler functions.
- Responses are returned via `TextContent` to ensure correct MCP typing.

### 🛡️ Central Safety Gate

- All policy decisions are centralized in `gate.py`.
- The gate enforces:
  - allowed verbs (`list`, `get`, `events`, `pod_logs`, `delete`)
  - scope requirements
  - forbidden kinds and endpoints
  - approval requirements for mutations

This gate is called **before any Kubernetes API interaction**. It is the single source of truth for allow/deny decisions.

---

## 📏 Safety Guarantees

The entire system enforces the following global rules:

### 🧱 Hard Safety Rules

1. **Safety is enforced in code**, not in prompts.
2. **Forbidden kinds** (like `Secret` and `ConfigMap`) can never be read, listed, or deleted.
3. **All tools require a namespace**; no cluster-wide read or write.
4. **No bulk operations** — no selectors, no multiple object deletes.
5. **Mutations require explicit approval** (`approved=true`) and return denial text if absent.
6. **One MCP tool call maps to exactly one Kubernetes API call**.
7. **Policy denials return text, not internal errors**.

These rules are enforced before any Kubernetes API call is allowed. They do not rely on prompts or heuristics.

---

## 📦 Tool Surface (Current)

The MCP server exposes these tools:

| Name             | Description                                                        |
|------------------|--------------------------------------------------------------------|
| `k8s_list`       | List namespaced Kubernetes resources (read-only)                   |
| `k8s_get`        | Get a single Kubernetes object by name                             |
| `k8s_list_events`| List events in a namespace                                          |
| `k8s_pod_logs`   | Read logs from a named pod                                         |
| `k8s_delete`     | Delete a single resource (requires `approved=true`)                 |

Each tool:
- accepts a JSON schema-validated input
- is enforced by the policy gate
- returns structured text output

There is **no exec into pods**, no watch streams, and no cluster-wide operations.

---

## 📁 Kubernetes API Access

- The implementation uses the **Kubernetes Python client** via `DynamicClient`.
- Resource resolution is dynamic — **no hardcoded resource lists**.
- Tools rely on API discovery to resolve `group/version/plural` to a Kubernetes resource.
- All pod logs and events also use official Kubernetes API calls.

These calls are executed only after successful policy enforcement.

---

## 📌 Observability & Errors

- Tool errors (including safety denials) are returned as **text content**, not protocol errors.
- Internal server errors (unexpected exceptions) also return text content describing the failure.
- No stack traces or uncaught exceptions are exposed via MCP.

This helps ensure MCP clients see a consistent, safe contract.

---

## ❌ Explicit Non-Goals

These are **by design**, not missing features:

- Reading **Secrets** or **ConfigMaps**
- Cluster-wide listing or deletion
- Selector-based bulk operations
- In-cluster execution of the MCP server
- Exec / port-forward / node OS logs
- Inference of intent or auto-approval from prompts

These limitations simplify the safety boundary and reduce blast radius.

---

## 🕊 Design Principles

1. **Fail-closed defaults**
   - If the safety gate cannot decide, the operation is blocked.

2. **One tool, one action**
   - Simplifies auditing, reasoning, and approval semantics.

3. **Deterministic control**
   - No heuristics, no pattern matching, no ML in policy.

4. **Explicit approvals**
   - Any mutation must be clearly approved (`approved=true`).

5. **Auditable text**
   - All denials articulate reason and requirements for success.

6. **Gate is authoritative**
   - No code path bypasses the policy gate.

---

## 🧩 Deployment

This server is intended to run as a **local access point for MCP clients** (like Claude Desktop or other agents).  
Production deployment may involve containerization and process supervision, but those concerns are outside the scope of this project.

---

## 📌 MCP Protocol Primitives

MCP defines:

- **Tools** — invocable commands
- **Resources** — contextual data sources
- **Prompts** — structured templates for model interaction

This agent implements only the **Tools** primitive in a minimal set. :contentReference[oaicite:1]{index=1}

---

## 🧪 Status

This architecture describes the **current system** as implemented — not an aspirational future.  
Phase planning beyond this (like controlled writes, audit logging, in-cluster execution) belongs in future documentation, not here.

---

## 📌 Summary

`mcp-k8s-agent` is a **safe, policy-first MCP server** for Kubernetes clusters that:

- Exposes a limited, deterministic set of Kubernetes operations
- Makes safety decisions in code
- Never exposes dangerous operations
- Returns structured text for all outcomes

This architecture is **the contract** — the code must always conform to it.
