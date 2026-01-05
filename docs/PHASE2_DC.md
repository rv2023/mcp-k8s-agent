# PHASE2_DELETE_DESIGN.md

Design doc for **Phase 2 — Delete-Only (Safe Mutations)** for `mcp-k8s-agent`.

This doc is written to match the project’s current philosophy:

- safety enforced in **code**, not prompts
- read-only by default
- no Secrets / ConfigMaps
- no cluster-wide ops
- no bulk ops
- no mutations unless explicitly approved
- one tool call = one Kubernetes API call
- deterministic outputs

Related docs in repo (context):
- ARCHITECTURE.md
- PHASE1_READ_DESIGN.md
- phase1_end.md

External references used in this doc:
- Kubernetes API concepts: https://kubernetes.io/docs/reference/using-api/api-concepts/
- Kubernetes API reference (generated): https://kubernetes.io/docs/reference/generated/kubernetes-api/
- Kubernetes Python client – CustomObjectsApi: https://github.com/kubernetes-client/python/blob/master/kubernetes/docs/CustomObjectsApi.md
- MCP tools spec: https://modelcontextprotocol.io/specification/ (see “Tools”)
- MCP transports (stdio): https://modelcontextprotocol.io/specification/ (see “Transports”)

---

## 0) Goals and non-goals

### Goals (Phase 2 delivers)
- Enable **delete of exactly one namespaced object** per tool call.
- Require an explicit, structured approval flag (`approved=true`).
- Keep deletions:
  - scoped to a single namespace
  - single-object only (no bulk)
  - blocked for forbidden kinds (Secret, ConfigMap)
  - deterministic and auditable

### Non-goals (explicitly out of scope for Phase 2)
- Create/apply/update/patch/scale
- Delete many objects at once (no label selector, no delete-collection)
- Cluster-scoped deletes
- Any note/logic that “tries to be smart” (no auto cleanups, no cascaded workflows)
- Allowing reads/writes of Secrets or ConfigMaps
- Any “kubectl exec” style tool

---

## 1) Current state (Phase 1 baseline)

### Files and responsibilities (today)
- `gate.py`
  - single safety authority (hard allow/deny)
  - blocks forbidden kinds (Secret, ConfigMap)
  - enforces namespace scoping
  - blocks cluster-scoped resources
  - blocks bulk semantics
  - blocks write operations unless `approved=True`

- `server.py`
  - MCP stdio server wiring
  - tool registration + dispatch
  - no Kubernetes logic inside

- `tools_read.py`
  - read-only tools for namespaced resources
  - one tool call = one API call
  - no Secret/ConfigMap

- `sanitize.py`
  - deterministic response trimming only
  - no “smart” logic

- `tools_write.py`
  - exists but empty (Phase 1)

- `phase1_smoke_test.py`, `test_client.py`
  - real validation paths

### Hard guarantees already enforced by code
- No Secrets / ConfigMaps
- No cluster-wide operations
- No bulk operations
- No mutations path exists (Phase 1)
- Namespace required
- One tool call = one Kubernetes API call

---

## 2) Phase 2 outcome (what will exist after Phase 2)

### New capability
- A delete tool that can delete **one namespaced object** by:
  - namespace
  - group/version
  - plural
  - name
  - approved=true

### Safety properties after Phase 2
- Deletes remain impossible unless:
  - `approved=true` is passed and validated
  - the request is for a namespaced resource
  - the kind is not forbidden
  - the request specifies a single object name

### What remains intentionally missing after Phase 2
- create/apply/patch/update/scale
- delete by label, deletecollection, “delete all pods”, “delete everything”
- cluster-scoped deletes
- Secret/ConfigMap access
- multi-step workflows

---

## 3) Public tool contract (what the MCP server exposes)

### Tool naming
Phase 2 adds **one** mutation tool:

- `k8s_delete`

Rationale:
- Phase 1 already supports “any namespaced resource” in a generic way.
- A generic delete tool matches Phase 1 and avoids growing a large tool surface.

---

## 4) Tool schema (inputs / outputs)

### 4.1 Inputs (required)
All fields are required unless explicitly marked optional.

- `namespace` (string, required)
  - must be non-empty
- `group` (string, required)
  - for core resources, use empty string `""`
  - examples: `"apps"`, `"batch"`, `"networking.k8s.io"`
- `version` (string, required)
  - examples: `"v1"`, `"v1beta1"`
- `plural` (string, required)
  - examples: `"pods"`, `"deployments"`, `"jobs"`
- `name` (string, required)
  - must be non-empty
- `approved` (boolean, required)
  - must be **actual boolean true**
  - if missing or not true => fail closed

### 4.2 Inputs (optional, safe)
These are optional because they can be risky if misused.

- `grace_period_seconds` (int, optional)
  - if not set, do not send it (let API default apply)
- `propagation_policy` (string, optional)
  - if not set, do not send it
  - if set, allow only: `"Foreground" | "Background" | "Orphan"`

Notes:
- Do **not** accept `labelSelector`, `fieldSelector`, or anything that implies “many objects”.
- Do **not** accept a “kind” string if the system already uses group/version/plural routing.

Kubernetes delete behavior is standard REST delete on an object URL:
- Concepts: https://kubernetes.io/docs/reference/using-api/api-concepts/
- Full reference: https://kubernetes.io/docs/reference/generated/kubernetes-api/

### 4.3 Output (deterministic)
Return a JSON object with:

- `request`
  - `namespace`, `group`, `version`, `plural`, `name`
- `result`
  - `status`: one of
    - `"deleted"` (delete accepted by API)
    - `"not_found"`
    - `"forbidden"`
    - `"rejected_by_gate"`
    - `"error"`
  - `message`: short human-readable line (no “assistant voice”)
- `raw`
  - sanitized Kubernetes API response body (trimmed via `sanitize.py`)

---

## 5) Gate rules (delete-specific)

`gate.py` remains the final authority. Phase 2 only adds support for validating a `"delete"` operation.

### 5.1 Required checks (must pass)
- `namespace` must be present and non-empty
- `name` must be present and non-empty
- resource must be namespaced (cluster-scoped blocked)
- `approved` must be present and must be boolean `true`
- kind must not be forbidden (`Secret`, `ConfigMap`)
- bulk semantics must be absent:
  - no `labelSelector`
  - no `fieldSelector`
  - no delete-collection endpoints
  - no wildcard names

### 5.2 Fail-closed behavior
If anything is missing or ambiguous, the gate must return a clear rejection:
- do not attempt the Kubernetes API call
- return a deterministic error payload

---

## 6) How delete maps to Kubernetes Python client

Phase 2 should use **one** Kubernetes API call per tool invocation.

Preferred approach (consistent with generic Phase 1):
- use the Kubernetes Python client’s generic/custom-object delete path so it works with:
  - built-in resources
  - CRDs
(while still requiring namespaced + gate allow)

Reference:
- https://github.com/kubernetes-client/python/blob/master/kubernetes/docs/CustomObjectsApi.md

Important constraints:
- Do not implement “list then delete”.
- Do not implement any loop deletes.
- Do not implement delete-collection.

---

## 7) Server wiring (registration + dispatch)

### 7.1 `server.py`
- register the new tool name `k8s_delete`
- dispatch to `tools_write.py`
- ensure gate is always called before executing delete

### 7.2 `tools_write.py`
- define the delete handler only
- call order for a delete request must be:
  1) `gate.check(...)`
  2) Kubernetes delete API call (exactly one)
  3) sanitize response
  4) return structured output

No other behavior is allowed in Phase 2.

---

## 8) Error handling rules (deterministic)

All error responses must be stable and structured.

### 8.1 Gate rejection
Examples:
- `approved` missing or false
- forbidden kind
- missing namespace/name
- cluster-scoped resource

Return:
- `status: "rejected_by_gate"`
- message includes a short reason
- no Kubernetes API call

### 8.2 Kubernetes API errors
- If API returns 404 => `status: "not_found"`
- If API returns 403 => `status: "forbidden"`
- Any other error => `status: "error"`

Do not hide raw errors, but keep output trimmed and deterministic via `sanitize.py`.

---

## 9) Test plan updates

Phase 2 extends the test suite with delete-only tests.

### 9.1 Update `phase1_smoke_test.py` OR add `phase2_smoke_test.py`
Recommended: add `phase2_smoke_test.py` so Phase 1 and Phase 2 remain independently verifiable.

### 9.2 Required tests
1) **Delete without approval fails**
- call `k8s_delete` with `approved=false` or missing
- expect `rejected_by_gate`

2) **Delete forbidden kinds fails**
- attempt delete for `Secret` and `ConfigMap`
- expect `rejected_by_gate`

3) **Delete cluster-scoped fails**
- attempt delete on a known cluster-scoped plural (example: `nodes`)
- expect `rejected_by_gate`

4) **Delete one real object succeeds**
- create a safe test object by hand (outside the tool), for example:
  - a Pod in `default` namespace
- call `k8s_delete` with `approved=true`
- expect `deleted`

5) **No bulk delete possible**
- ensure tool schema does not accept selectors
- ensure deletecollection route is not exposed
- attempt “delete all” style inputs and verify rejection

---

## 10) Security notes (why this phase is safe)

Phase 2 adds only one new risk surface: deletion.

Mitigations built-in:
- explicit approval required (`approved=true`)
- one object per call (name required)
- gate blocks forbidden kinds, cluster-scope, and bulk patterns
- deterministic behavior and deterministic outputs
- no tool supports multi-step logic

---

## 11) Definition of done (Phase 2)

Phase 2 is “done” when:
- `k8s_delete` is registered and callable via MCP
- gate rejects unsafe or ambiguous delete requests
- a real cluster test proves:
  - delete requires approval
  - forbidden kinds blocked
  - cluster-scoped blocked
  - single-object delete works
  - no bulk deletes are possible
- docs updated:
  - README includes Phase 2 summary and guarantees
  - ARCHITECTURE.md updated only if needed to reflect tool list and phase boundary

---

## 12) Roadmap after Phase 2 (high-level)

- Phase 3: Create/apply (tight allowlist of kinds, approved=true)
- Phase 4: Intent-based safe actions (scale/restart with strict params)
- Phase 5: bounded multi-step flows (each step explicit and gated)

Each phase must preserve:
- safety in code
- deterministic results
- no bulk destructive actions
- namespace scoping
- no Secret/ConfigMap access