# gate.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# Same as old eks-agent
FORBIDDEN_KINDS = {"secret", "configmap"}  # :contentReference[oaicite:2]{index=2}

# Basic write verbs (cluster mutation) – forbidden unless explicitly approved.
WRITE_VERBS = {
    "create",
    "apply",
    "update",
    "patch",
    "delete",
    "replace",
    "scale",
    "restart",
    "rollout_restart",
    "cordon",
    "drain",
    "taint",
    "label",
    "annotate",
}


@dataclass(frozen=True)
class RequestContext:
    """
    Context you pass into the gate for every tool call.
    """
    tool_name: str                 # e.g. "k8s_read" / "k8s_delete_pod"
    verb: str                      # e.g. "read" / "list" / "delete"
    kind: Optional[str] = None     # e.g. "Pod", "Deployment", "Secret"
    namespace: Optional[str] = None
    name: Optional[str] = None
    approved: bool = False         # user explicitly approved this specific action


class GateError(Exception):
    pass


class ForbiddenKind(GateError):
    pass


class MissingScope(GateError):
    pass


class ApprovalRequired(GateError):
    pass


def normalize_kind(kind: Optional[str]) -> Optional[str]:
    return kind.lower() if kind else None


def normalize_verb(verb: str) -> str:
    return verb.strip().lower()


def is_write(verb: str) -> bool:
    v = normalize_verb(verb)
    return v in WRITE_VERBS


def validate_kind(kind: Optional[str]) -> None:
    """
    Hard block: never allow Secret/ConfigMap reads (or writes).
    """
    k = normalize_kind(kind)
    if k and k in FORBIDDEN_KINDS:
        raise ForbiddenKind(f"Access to kind '{kind}' is forbidden")


def validate_scope(ctx: RequestContext) -> None:
    """
    Scope rules (safe defaults):
    - LIST requires namespace (no cluster-wide scraping by default)
    - Object-specific actions require namespace + name
    """
    verb = normalize_verb(ctx.verb)

    if verb == "list":
        if not ctx.namespace:
            raise MissingScope("LIST requires a namespace (cluster-wide list is blocked by default)")
        return

    # For non-list operations, if a kind is provided, require namespace+name
    if ctx.kind:
        if not ctx.namespace or not ctx.name:
            raise MissingScope("This action requires both namespace and name")


def require_approval_if_write(ctx: RequestContext) -> None:
    """
    Old eks-agent forbids mutation; for your new MCP server:
    - allow write actions ONLY if approved=True
    """
    if is_write(ctx.verb) and not ctx.approved:
        raise ApprovalRequired(
            f"Write action '{ctx.verb}' blocked. Re-run with approved=true."
        )


def enforce(ctx: RequestContext) -> None:
    """
    One call that applies all gates.
    """
    validate_kind(ctx.kind)
    validate_scope(ctx)
    require_approval_if_write(ctx)
