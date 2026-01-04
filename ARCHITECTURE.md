# mcp-k8s-agent — Architecture

This document defines the **final architecture and phased design** of `mcp-k8s-agent`.

It is frozen as the authoritative reference for:
- safety guarantees
- phase boundaries
- allowed and forbidden behavior
- long-term design intent

No implementation details in this document override `gate.py`.

---

## Project Summary

`mcp-k8s-agent` is a **Model Context Protocol (MCP) server** that exposes Kubernetes capabilities safely to AI clients (Cursor, Claude Desktop, etc.).

Core design principles:

- Safety enforced in **code**, not prompts
- Read-only by default
- No access to Secrets or ConfigMaps
- No cluster-wide operations
- No bulk actions
- No mutations without explicit approval
- Deterministic and auditable behavior

---

## Hard Safety Rules (Global)

These rules apply to **all phases** and **all tools**:

1. `gate.py` is the final authority for allow/deny
2. Forbidden kinds are **never accessible** (read, delete, write)
   - Current forbidden list includes:
     - `Secret`
     - `ConfigMap`
3. Every tool call **must include `namespace`**
4. No cluster-wide reads or writes
5. No bulk operations (no selectors, no collections)
6. No implicit approvals
7. Any mutation requires `approved=true`
8. One tool call maps to **one Kubernetes API action**
9. Safety decisions are deterministic

Kubernetes API reference:  
https://kubernetes.io/docs/reference/kubernetes-api/

### Central Safety Gate (gate.py)

All Kubernetes access — including reads, events, and logs — is enforced through
a single policy gate implemented in `gate.py`.

Every tool call constructs a `RequestContext` and must pass `enforce()` **before**
any Kubernetes API interaction occurs.

This includes:
- standard read operations (`get`, `list`)
- event retrieval
- pod log access
- delete operations (Phase 2)

There are no exceptions or bypass paths.
---

#### Logs and Events

The agent supports Kubernetes-native observability only:

- Namespace-scoped events
- Pod stdout/stderr logs via the Kubernetes API

Constraints:
- Pod logs require explicit `namespace` and `pod` name
- Logs are available in all namespaces, including `kube-system`
- Node OS logs, kubelet logs, and host-level logs are **not accessible**
- No cloud provider logs (e.g., CloudWatch / CloudTrail)

All log and event access is routed through the central safety gate.

### Explicit Non-Goals

The following are intentional non-goals of this system:

- Accessing Secrets or ConfigMaps
- Executing commands inside pods
- Reading node or host OS logs
- SSH / SSM access to nodes
- Accessing cloud provider logs
- Cluster-wide scraping or bulk operations
- Multi-object fan-out behind a single tool

These are architectural decisions, not missing features.



## Phase 0 — Current State (Completed)

### What exists today
- MCP server wiring (`server.py`)
- Central safety gate (`gate.py`)
- Forbidden kind enforcement
- Namespace enforcement
- Write blocking unless approved
- Tool registration infrastructure

### What is intentionally missing
- Kubernetes Python client
- Read tools
- Delete tools
- Write tools
- Audit logging
- In-cluster execution

This phase proves **control before capability**.

---

## Phase 1 — Read-Only Access  
**(Any resource except forbidden list)**

### Goal
Allow safe, namespaced, read-only access to **any Kubernetes resource**, including CRDs, except forbidden kinds.

### Capabilities added
- Read operations:
  - list
  - get
  - events
  - logs (scoped, namespaced)
- Works for:
  - Core resources
  - Grouped resources
  - CRDs

### Hard limits
- No access to `Secret` or `ConfigMap`
- No cluster-scoped reads
- No cross-namespace reads
- No bulk scraping
- No selector-based reads

### Why this phase exists
- Enables troubleshooting and visibility
- Zero mutation risk
- Builds trust in the safety model

Kubernetes API structure reference:  
https://kubernetes.io/docs/reference/using-api/api-concepts/

---

## Phase 2 — Delete-Only Mutations  
**(Any resource except forbidden list)**

### Goal
Allow deletion of **exactly one Kubernetes object per call**, with explicit approval.

### Capabilities added
- Delete a single resource instance
- Works for:
  - Built-in resources
  - CRDs

### Required inputs
- `namespace`
- `name`
- `group`
- `version`
- `plural`
- `approved=true`

### Explicitly forbidden
- No delete-by-label
- No delete-collection
- No wildcards
- No cross-namespace deletes
- No force delete
- No cascading mode toggles exposed

Kubernetes delete behavior reference:  
https://kubernetes.io/docs/reference/using-api/api-concepts/#deleting-resources

Phase 2 extends safety guarantees by enforcing the same gate policies
for events and pod log access, ensuring all observability flows through
a single deterministic control point.

### Optional safety
- `dry_run=true` support for validation without persistence

Dry-run reference:  
https://kubernetes.io/docs/reference/using-api/api-concepts/#dry-run

### Why this phase exists
Deletes are common but dangerous.  
This phase enforces:
- explicit identity
- explicit approval
- zero blast-radius amplification

---

## Phase 3 — Controlled Writes  
**(Any resource except forbidden list)**

### Goal
Allow controlled creation and modification of **one Kubernetes object at a time**, with approval.

### Capabilities added
- Create one resource
- Update one resource
- Patch one resource
- Works for:
  - Core resources
  - Grouped resources
  - CRDs

### Required inputs
- `namespace`
- `group`
- `version`
- `plural`
- `approved=true`
- Object payload (`body`)

### Safety constraints
- One object per call
- No bulk apply
- No directory apply
- No selector-based writes
- Payload size limits enforced
- Gate enforced before execution

### Intentionally missing
- Server-side apply (SSA)
- Namespace creation
- RBAC changes
- CRD creation
- Webhooks

Apply vs patch reference:  
https://kubernetes.io/docs/reference/using-api/server-side-apply/

### Why this phase exists
Writes can:
- spawn controllers
- alter security posture
- cause indirect fan-out

This phase keeps writes:
- explicit
- bounded
- auditable

---

## Phase 4 — Audit and Traceability

### Goal
Make **every action observable and reviewable**.

### Capabilities added
- Structured audit records including:
  - tool name
  - timestamp
  - namespace
  - resource identity
  - approved flag
  - allow/deny decision

### Non-goals
- No behavior inference
- No auto-remediation
- No policy learning

### Why this phase exists
AI access to Kubernetes requires:
- accountability
- forensic visibility
- compliance readiness

---

## Phase 5 — In-Cluster Execution (Optional)

### Goal
Support running the MCP server **inside a Kubernetes cluster**.

### Capabilities added
- In-cluster authentication
- Same tool surface
- Same gate enforcement
- Same forbidden list

Config loading reference:  
https://github.com/kubernetes-client/python/blob/master/examples/in_cluster_config.py

### Why separate
In-cluster execution increases blast radius and must remain explicit.

---

## Final System Guarantees

When all phases are complete, the system guarantees:

- No access to forbidden kinds
- No cluster-wide actions
- No bulk operations
- No hidden side effects
- No implicit approvals
- No prompt-based safety
- Deterministic behavior
- One tool call = one Kubernetes API action
- Full auditability

---

## Explicit Refusals (By Design)

The system will **never**:

- Read Secrets or ConfigMaps
- Exec into pods
- Port-forward
- Modify RBAC
- Apply directories
- Infer intent
- Auto-approve actions
- Execute multi-step plans
- Act outside declared MCP tools

---

## Status

This document is **frozen**.

Any changes require:
- an explicit phase proposal
- a documented safety justification
- no silent expansion of capabilities