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
# Patch policy (Phase 4)
# -----------------------------
PATCH_ACTIONS = {"scale", "update_image", "rollout_restart"}

# Restrict patch to known workload built-ins only (v1)
PATCH_ALLOWED_PLURALS_BY_ACTION = {
    "scale": {"deployments", "statefulsets"},
    "update_image": {"deployments", "statefulsets", "daemonsets"},
    "rollout_restart": {"deployments", "statefulsets", "daemonsets"},
}

# replicas safety bound (v1)
SCALE_MIN_REPLICAS = 0
SCALE_MAX_REPLICAS = 100


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


class InvalidPatchIntent(GateError):
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

    # get / delete / logs / patch → object scoped
    if verb in {"get", "delete", "pod_logs", "patch"}:
        if not ctx.namespace or not ctx.name:
            raise MissingScope(f"{verb.upper()} requires namespace and name")
        return


def require_approval_if_write(ctx: RequestContext) -> None:
    if ctx.verb in {"delete", "patch"} and not ctx.approved:
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


def _require_str(arguments: Mapping[str, Any], key: str) -> str:
    val = arguments.get(key)
    if not isinstance(val, str) or not val.strip():
        raise InvalidPatchIntent(f"PATCH requires non-empty '{key}'")
    return val.strip()


def _require_int(arguments: Mapping[str, Any], key: str) -> int:
    val = arguments.get(key)
    if not isinstance(val, int):
        raise InvalidPatchIntent(f"PATCH requires integer '{key}'")
    return val


def validate_patch_intent(ctx: RequestContext) -> None:
    """
    Validate Phase 4 intent-only patch input.
    No raw patch payloads are accepted.
    """
    if not ctx.arguments:
        raise InvalidPatchIntent("PATCH missing arguments")

    args = ctx.arguments

    action = args.get("action")
    if not isinstance(action, str) or action not in PATCH_ACTIONS:
        raise InvalidPatchIntent("PATCH requires action in {scale, update_image, rollout_restart}")

    plural = args.get("plural")
    if not isinstance(plural, str) or not plural.strip():
        raise InvalidPatchIntent("PATCH requires 'plural'")
    plural_n = plural.strip().lower()

    allowed_plurals = PATCH_ALLOWED_PLURALS_BY_ACTION[action]
    if plural_n not in allowed_plurals:
        raise InvalidPatchIntent(f"PATCH action '{action}' not allowed for plural '{plural}'")

    # Enforce explainability: required params per action
    if action == "scale":
        replicas = _require_int(args, "replicas")
        if replicas < SCALE_MIN_REPLICAS or replicas > SCALE_MAX_REPLICAS:
            raise InvalidPatchIntent(f"PATCH scale replicas must be between {SCALE_MIN_REPLICAS} and {SCALE_MAX_REPLICAS}")

    elif action == "update_image":
        _require_str(args, "container")
        _require_str(args, "image")

    elif action == "rollout_restart":
        # optional "reason" allowed, but must be small if present
        reason = args.get("reason")
        if reason is not None:
            if not isinstance(reason, str):
                raise InvalidPatchIntent("PATCH reason must be a string")
            if len(reason) > 200:
                raise InvalidPatchIntent("PATCH reason too long (max 200 chars)")


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

    # Patch-specific policy
    if ctx.verb == "patch":
        validate_patch_intent(ctx)