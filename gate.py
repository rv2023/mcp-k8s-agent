from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Mapping, Any


# -----------------------------
# Hard forbidden resources
# -----------------------------

FORBIDDEN_KINDS = {
    "secret",
    "configmap",
}

# Block bypass when clients omit `kind`
FORBIDDEN_PLURALS = {
    "secrets",
    "configmaps",
}


# -----------------------------
# Exceptions
# -----------------------------

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


# -----------------------------
# Request Context
# -----------------------------

@dataclass(frozen=True)
class RequestContext:
    tool_name: str
    verb: str
    kind: Optional[str] = None
    namespace: Optional[str] = None
    name: Optional[str] = None
    approved: bool = False
    arguments: Optional[Mapping[str, Any]] = None


# -----------------------------
# Normalizers
# -----------------------------

def _norm(val: Optional[str]) -> Optional[str]:
    return val.lower().strip() if val else None


# -----------------------------
# Validators
# -----------------------------

def validate_allowed_action(ctx: RequestContext) -> None:
    # All actions are explicitly enumerated by tools
    if not ctx.verb:
        raise GateError("Missing verb")


def validate_kind(kind: Optional[str]) -> None:
    k = _norm(kind)
    if k and k in FORBIDDEN_KINDS:
        raise ForbiddenKind(f"Access to kind '{kind}' is forbidden")


def validate_plural(plural: Optional[str]) -> None:
    p = _norm(plural)
    if p and p in FORBIDDEN_PLURALS:
        raise ForbiddenKind(f"Access to plural '{plural}' is forbidden")


def validate_scope(ctx: RequestContext) -> None:
    verb = ctx.verb

    # list → must be namespaced
    if verb == "list":
        if not ctx.namespace:
            raise MissingScope("LIST requires a namespace")
        return

    # events → namespaced diagnostics
    if verb == "events":
        if not ctx.namespace:
            raise MissingScope("EVENTS requires a namespace")
        return

    # get / delete / logs → object scoped
    if verb in {"get", "delete", "pod_logs"}:
        if not ctx.namespace or not ctx.name:
            raise MissingScope(f"{verb.upper()} requires namespace and name")
        return


def require_approval_if_write(ctx: RequestContext) -> None:
    if ctx.verb in {"delete"} and not ctx.approved:
        raise ApprovalRequired("Mutation requires approved=true")


def block_bulk_args(arguments: Mapping[str, Any]) -> None:
    forbidden = {
        "label_selector",
        "field_selector",
        "selectors",
        "all",
        "all_namespaces",
    }
    for key in forbidden:
        if key in arguments:
            raise BulkOperationBlocked(f"Bulk operation via '{key}' is not allowed")


# -----------------------------
# Single Enforcement Entry
# -----------------------------

def enforce(ctx: RequestContext) -> None:
    """
    Single fail-closed enforcement point.
    Called exactly once per tool invocation.
    """

    validate_allowed_action(ctx)

    # Hard blocks
    validate_kind(ctx.kind)
    if ctx.arguments:
        validate_plural(ctx.arguments.get("plural"))

    # Scope + approval
    validate_scope(ctx)
    require_approval_if_write(ctx)

    # Bulk protections
    if ctx.arguments:
        block_bulk_args(ctx.arguments)