from __future__ import annotations

import json
from typing import Any, Dict

from kubernetes import client, config
from kubernetes.dynamic import DynamicClient

from gate import RequestContext, enforce
from sanitize import prune_k8s_object


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def _load_dynamic() -> DynamicClient:
    # Local kubeconfig only (current project assumption)
    config.load_kube_config()
    api_client = client.ApiClient()
    return DynamicClient(api_client)


def _api_version(group: str, version: str) -> str:
    group = (group or "").strip()
    version = (version or "").strip()
    return version if group == "" else f"{group}/{version}"


def _resolve_resource(
    dyn: DynamicClient,
    api_version: str,
    *,
    kind: str | None,
    plural: str,
):
    """
    Resolve a dynamic resource safely across kubernetes client versions.

    Priority:
    1. Use kind if provided
    2. Fall back to plural name lookup
    """
    if kind:
        return dyn.resources.get(api_version=api_version, kind=kind)

    for r in dyn.resources:
        if r.api_version == api_version and r.name == plural:
            return r

    raise ValueError(f"Resource not found: {api_version}/{plural}")


# -------------------------------------------------------------------
# Write tool
# -------------------------------------------------------------------

async def k8s_delete(arguments: Dict[str, Any]) -> str:
    """
    Delete exactly one namespaced object.

    Required:
      - namespace, group, version, plural, name, approved=true

    Optional:
      - grace_period_seconds
      - propagation_policy
    """
    namespace = (arguments.get("namespace") or "").strip()
    group = (arguments.get("group") or "").strip()
    version = (arguments.get("version") or "").strip()
    plural = (arguments.get("plural") or "").strip()
    name = (arguments.get("name") or "").strip()
    kind = arguments.get("kind")
    approved = bool(arguments.get("approved", False))

    ctx = RequestContext(
        tool_name="k8s_delete",
        verb="delete",
        kind=kind,
        namespace=namespace,
        name=name,
        approved=approved,
    )

    # Gate first: fail closed, no API call if rejected.
    enforce(ctx, arguments=arguments)

    if not namespace or not name:
        raise ValueError("namespace and name are required")

    if not plural or not version:
        raise ValueError("group/version/plural are required")

    dyn = _load_dynamic()
    api_version = _api_version(group, version)

    resource = _resolve_resource(
        dyn,
        api_version,
        kind=kind,
        plural=plural,
    )

    delete_opts = client.V1DeleteOptions()

    if "grace_period_seconds" in arguments and arguments["grace_period_seconds"] is not None:
        delete_opts.grace_period_seconds = int(arguments["grace_period_seconds"])

    if "propagation_policy" in arguments and arguments["propagation_policy"] is not None:
        delete_opts.propagation_policy = str(arguments["propagation_policy"])

    try:
        resp = resource.delete(
            name=name,
            namespace=namespace,
            body=delete_opts,
        )

        raw = resp.to_dict() if hasattr(resp, "to_dict") else resp

        out = {
            "request": {
                "namespace": namespace,
                "group": group,
                "version": version,
                "plural": plural,
                "name": name,
            },
            "result": {
                "status": "deleted",
                "message": "delete accepted",
            },
            "raw": prune_k8s_object(raw if isinstance(raw, dict) else {"value": raw}),
        }
        return json.dumps(out, indent=2, sort_keys=True)

    except client.exceptions.ApiException as e:
        status = "error"
        if e.status == 404:
            status = "not_found"
        elif e.status == 403:
            status = "forbidden"

        out = {
            "request": {
                "namespace": namespace,
                "group": group,
                "version": version,
                "plural": plural,
                "name": name,
            },
            "result": {
                "status": status,
                "message": f"kubernetes api error: {e.status}",
            },
            "raw": {
                "status": e.status,
                "reason": e.reason,
                "body": e.body,
            },
        }
        return json.dumps(out, indent=2, sort_keys=True)
