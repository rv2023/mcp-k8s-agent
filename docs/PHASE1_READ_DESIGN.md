# PHASE1_READ_DESIGN.md

## Phase 1 — Read-Only Access (Design Spec)

This document defines **Phase 1** of `mcp-k8s-agent`.

Rules:
- **No code** in this document
- Grounded in the frozen architecture (`ARCHITECTURE.md`)
- Read-only tools only
- `gate.py` is enforced for every call
- Every call must include `namespace`
- Read applies to **any namespaced Kubernetes resource** **except forbidden kinds**
  - Forbidden list currently includes: `Secret`, `ConfigMap`

Kubernetes API reference (authoritative):  
https://kubernetes.io/docs/reference/kubernetes-api/

---

## 1) Phase 1 goals

After Phase 1, the server must support safe troubleshooting by allowing:

- Read-only access to **any namespaced resource type** (core, grouped, CRDs)
- Read operations:
  - list resources
  - get a single resource
  - read resource status (if supported)
  - list namespace events
  - read pod logs (scoped)

After Phase 1, the server must NOT support:

- Any mutation (create/update/patch/delete)
- Reading `Secret` or `ConfigMap`
- Cluster-wide reads
- Cross-namespace reads
- Bulk scraping
- Selector-based listing
- Streaming/watch APIs

---

## 2) Phase 1 design principle

**One MCP tool call maps to exactly one Kubernetes READ API call.**

No chaining.  
No hidden retries.  
No auto-fallback behavior.

This keeps behavior:
- deterministic
- auditable
- easy to debug

---

## 3) Resource addressing model (required)

Because Phase 1 must support **any resource**, tools must not hardcode Pods/Deployments/etc.

Every generic read tool MUST accept the identity fields below:

| Field | Required | Notes |
|------|----------|-------|
| `namespace` | yes | Mandatory by project rule and gate |
| `group` | yes | Empty string allowed for core (`/api/v1`) |
| `version` | yes | Example: `v1`, `v1beta1` |
| `plural` | yes | Example: `pods`, `deployments` |
| `name` | depends | Required for single-object reads |

Kubernetes API structure reference:  
https://kubernetes.io/docs/reference/using-api/api-concepts/

---

## 4) Phase 1 tool list (exact)

### 4.1 `list_resources`

**Purpose**  
List objects of a given resource type within a **single namespace**.

**Inputs**
- `namespace` (required)
- `group` (required; empty for core)
- `version` (required)
- `plural` (required)

**Behavior**
- Lists only within `namespace`
- Gate validates request (forbidden kinds + namespace presence)
- No selectors
- No pagination controls (initially)

**Maps to**
- `GET /api.../namespaces/{namespace}/{plural}`

API reference:  
https://kubernetes.io/docs/reference/kubernetes-api/

---

### 4.2 `get_resource`

**Purpose**  
Fetch a **single object** by name.

**Inputs**
- `namespace` (required)
- `group` (required)
- `version` (required)
- `plural` (required)
- `name` (required)

**Behavior**
- Exact object lookup only
- Gate blocks forbidden kinds
- No fallback behavior

**Maps to**
- `GET /api.../namespaces/{namespace}/{plural}/{name}`

---

### 4.3 `get_resource_status`

**Purpose**  
Return the `.status` portion of a resource (if present).

Reason: Keeps “read status” intent explicit and avoids returning full spec when not needed.

**Inputs**
- Same as `get_resource`

**Behavior**
- Returns `.status` only
- If resource does not expose status → deterministic error

Status subresource reference:  
https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/#status-subresource

---

### 4.4 `list_events`

**Purpose**  
Read events within a **single namespace**.

**Inputs**
- `namespace` (required)

**Hard limits**
- No selectors initially
- Namespace-only

**Maps to**
- Core Events API

Events reference:  
https://kubernetes.io/docs/reference/kubernetes-api/cluster-resources/event-v1/

---

### 4.5 `get_pod_logs`

**Purpose**  
Fetch logs for **one pod** (and optionally one container) within a namespace.

**Inputs**
- `namespace` (required)
- `pod_name` (required)
- `container` (optional)
- `tail_lines` (optional; bounded)
- `since_seconds` (optional)

**Hard limits**
- Single pod only
- No streaming
- No “all containers”
- No “previous” logs unless explicitly added later

Logs reference:  
https://kubernetes.io/docs/reference/kubernetes-api/workload-resources/pod-v1/#read-log

---

## 5) Forbidden list enforcement (Phase 1)

`gate.py` rules apply unchanged.

If the request targets:
- `Secret` or `ConfigMap` (or any future forbidden kind)
→ The call is denied before any Kubernetes API call occurs.

No exceptions for read.

---

## 6) Error behavior (deterministic)

Phase 1 tools must return predictable errors, without retries:

- `ForbiddenError` — gate denial
- `NotFound` — Kubernetes 404
- `InvalidRequest` — missing required fields
- `UpstreamError` — Kubernetes API errors propagated clearly

No automatic retries.  
No inferred next steps.

---

## 7) Explicit non-goals for Phase 1

Even though Kubernetes supports these, Phase 1 intentionally excludes:

- label selectors / field selectors
- pagination controls
- watch / streaming
- cluster-scoped resources
- CRD discovery helpers
- OpenAPI schema access

These increase blast radius or complexity and require separate justification later.

---

## 8) Phase 1 completion criteria (“done”)

Phase 1 is complete when:

- All Phase 1 read tools exist and function
- Every tool call requires `namespace`
- Every tool call enforces `gate.py`
- Forbidden kinds are always blocked
- No write/delete tool is present or callable
- One tool call maps to one Kubernetes API call
- Output and errors are deterministic and auditable