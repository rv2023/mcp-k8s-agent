from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Mapping, Any


# -------------------------------------------------------------------
# Absolute forbidden kinds (read or write)
# -------------------------------------------------------------------

FORBIDDEN_KINDS = {
    "secret",
    "configmap",
}


# -------------------------------------------------------------------
# Write verbs (cluster mutation)
# -------------------------------------------------------------------

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


# -------------------------------------------------------------------
# Read-only verbs we explicitly allow
# -------------------------------------------------------------------

READ_VERBS = {
    "get",
    "list",
    "events",
    "pod_logs",
}


# -------------------------------------------------------------------
# Request context
# -------------------------------------------------------------------

@dataclass(frozen=True)
class RequestContext:
    """
    Context passed into the gate for every tool call.
    """
    tool_name: str
    verb: str
    kind: Optional[str] = None
    namespace: Optional[str] = None
    name: Optional[str] = None
    approved: bool = False


# -------------------------------------------------------------------
# Gate errors
# -------------------------------------------------------------------

class GateError(Exception):
    pass


class ForbiddenKind(GateError):
    pass


class MissingScope(GateError):
    pass


class ApprovalRequired(GateError):
    pass


class BulkOperationBlocked(GateError):
    pass


class ActionNotAllowed(GateError):
    pass


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def normalize_kind(kind: Optional[str]) -> Optional[str]:
    return kind.lower().strip() if kind else None


def normalize_verb(verb: str) -> str:
    return verb.strip().lower()


def is_write(verb: str) -> bool:
    return normalize_verb(verb) in WRITE_VERBS


# -------------------------------------------------------------------
# Validators
# -------------------------------------------------------------------

def validate_kind(kind: Optional[str]) -> None:
    """
    Hard block: never allow Secret / ConfigMap access.
    """
    k = normalize_kind(kind)
    if k and k in FORBIDDEN_KINDS:
        raise ForbiddenKind(f"Access to kind '{kind}' is forbidden")


def validate_scope(ctx: RequestContext) -> None:
    """
    Scope rules:

    - Nodes are cluster-scoped and allowed for get/list
    - pod_logs requires namespace + pod name
    - list/get/events require namespace for non-node resources
    """
    verb = normalize_verb(ctx.verb)

    # Allow node describe (get/list nodes)
    if normalize_kind(ctx.kind) == "node":
        if verb in {"get", "list"}:
            return

    # pod logs: must be fully scoped
    if verb == "pod_logs":
        if not ctx.namespace or not ctx.name:
            raise MissingScope("pod_logs requires namespace and pod name")
        return

    # list: must be namespaced
    if verb == "list":
        if not ctx.namespace:
            raise MissingScope("LIST requires a namespace")
        return

    # get / delete / events: must be object-scoped
    if verb in {"get", "delete", "events"}:
        if not ctx.namespace or not ctx.name:
            raise MissingScope(f"{verb.upper()} requires namespace and name")
        return

    # Fallback safety
    if ctx.kind:
        if not ctx.namespace or not ctx.name:
            raise MissingScope("This action requires namespace and name")


def require_approval_if_write(ctx: RequestContext) -> None:
    """
    Write actions require explicit approval.
    """
    if is_write(ctx.verb) and not ctx.approved:
        raise ApprovalRequired(
            f"Write action '{ctx.verb}' blocked. Re-run with approved=true."
        )


def validate_allowed_action(ctx: RequestContext) -> None:
    """
    Explicit allow-list.
    Anything not here is blocked.
    """
    verb = normalize_verb(ctx.verb)

    if verb in READ_VERBS:
        return

    if verb in WRITE_VERBS:
        return

    raise ActionNotAllowed(f"Action '{ctx.verb}' is not permitted")


def block_bulk_args(arguments: Mapping[str, Any]) -> None:
    """
    Hard block any bulk / selector-based operations.
    """
    forbidden_fields = {
        "labelSelector",
        "label_selector",
        "fieldSelector",
        "field_selector",
        "selector",
    }

    for f in forbidden_fields:
        if f in arguments and arguments.get(f):
            raise BulkOperationBlocked(
                f"Bulk operation field '{f}' is blocked"
            )


# -------------------------------------------------------------------
# Entry point
# -------------------------------------------------------------------

def enforce(ctx: RequestContext, arguments: Optional[Mapping[str, Any]] = None) -> None:
    """
    Single policy enforcement entry point.
    """
    validate_allowed_action(ctx)
    validate_kind(ctx.kind)
    validate_scope(ctx)
    require_approval_if_write(ctx)

    if arguments is not None:
        block_bulk_args(arguments)