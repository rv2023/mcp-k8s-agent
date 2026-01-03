# tools_read.py
from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, Dict, Optional, Tuple

from kubernetes import client, config

from gate import RequestContext, enforce
from sanitize import prune_k8s_object

# Extra hard safety: forbid by plural too (because gate.py forbids by kind).
_FORBIDDEN_PLURALS = {"secrets", "configmaps"}

# Kubeconfig should be loaded once per process.
_K8S_READY = False


class K8sToolError(Exception):
    pass


class ForbiddenResource(K8sToolError):
    pass


class InvalidRequest(K8sToolError):
    pass


def _ensure_kubeconfig_loaded() -> None:
    global _K8S_READY
    if _K8S_READY:
        return
    # Local-only (as you confirmed)
    config.load_kube_config()
    _K8S_READY = True


def _base_path(group: str, version: str) -> str:
    group = (group or "").strip()
    version = (version or "").strip()
    if not version:
        raise InvalidRequest("version is required")
    if group == "":
        return f"/api/{version}"
    return f"/apis/{group}/{version}"


def _namespaced_resource_path(
    *, group: str, version: str, namespace: str, plural: str, name: Optional[str] = None, subresource: Optional[str] = None
) -> str:
    if not namespace:
        raise InvalidRequest("namespace is required")
    if not plural:
        raise InvalidRequest("plural is required")

    plural_l = plural.strip().lower()
    if plural_l in _FORBIDDEN_PLURALS:
        raise ForbiddenResource(f"Access to resource '{plural}' is forbidden")

    base = _base_path(group, version)
    path = f"{base}/namespaces/{namespace}/{plural_l}"
    if name:
        path += f"/{name}"
    if subresource:
        path += f"/{subresource}"
    return path


def _call_k8s_get(path: str, query_params: Optional[list] = None) -> Dict[str, Any]:
    """
    One HTTP call to the Kubernetes API.
    """
    _ensure_kubeconfig_loaded()
    api_client = client.ApiClient()

    # call_api returns: (data, status_code, headers)
    data, _, _ = api_client.call_api(
        path,
        "GET",
        query_params=query_params or [],
        header_params={"Accept": "application/json"},
        response_type="object",
        auth_settings=["BearerToken"],
        _preload_content=True,
    )
    # data is already a Python object (dict/list)
    return data if isinstance(data, dict) else {"items": data}


def _json_text(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, default=str)


def list_resources(
    *,
    namespace: str,
    group: str,
    version: str,
    plural: str,
    kind: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Returns (content_type, text)
    """
    ctx = RequestContext(
        tool_name="list_resources",
        verb="list",
        kind=kind,
        namespace=namespace,
        name=None,
        approved=False,
    )
    enforce(ctx)

    path = _namespaced_resource_path(group=group, version=version, namespace=namespace, plural=plural)
    data = _call_k8s_get(path)
    return ("application/json", _json_text(prune_k8s_object(data)))


def get_resource(
    *,
    namespace: str,
    group: str,
    version: str,
    plural: str,
    name: str,
    kind: Optional[str] = None,
) -> Tuple[str, str]:
    ctx = RequestContext(
        tool_name="get_resource",
        verb="read",
        kind=kind,
        namespace=namespace,
        name=name,
        approved=False,
    )
    enforce(ctx)

    path = _namespaced_resource_path(group=group, version=version, namespace=namespace, plural=plural, name=name)
    data = _call_k8s_get(path)
    return ("application/json", _json_text(prune_k8s_object(data)))


def get_resource_status(
    *,
    namespace: str,
    group: str,
    version: str,
    plural: str,
    name: str,
    kind: Optional[str] = None,
) -> Tuple[str, str]:
    ctx = RequestContext(
        tool_name="get_resource_status",
        verb="read",
        kind=kind,
        namespace=namespace,
        name=name,
        approved=False,
    )
    enforce(ctx)

    path = _namespaced_resource_path(
        group=group,
        version=version,
        namespace=namespace,
        plural=plural,
        name=name,
        subresource="status",
    )
    data = _call_k8s_get(path)
    return ("application/json", _json_text(prune_k8s_object(data)))


def list_events(*, namespace: str) -> Tuple[str, str]:
    """
    Phase 1: namespace events only.

    We use core events: group="" version="v1" plural="events"
    """
    ctx = RequestContext(
        tool_name="list_events",
        verb="list",
        kind="Event",
        namespace=namespace,
        name=None,
        approved=False,
    )
    enforce(ctx)

    path = _namespaced_resource_path(group="", version="v1", namespace=namespace, plural="events")
    data = _call_k8s_get(path)
    return ("application/json", _json_text(prune_k8s_object(data)))


def get_pod_logs(
    *,
    namespace: str,
    pod_name: str,
    container: Optional[str] = None,
    tail_lines: Optional[int] = 200,
    since_seconds: Optional[int] = None,
) -> Tuple[str, str]:
    """
    One API call to fetch pod logs.
    """
    ctx = RequestContext(
        tool_name="get_pod_logs",
        verb="read",
        kind="Pod",
        namespace=namespace,
        name=pod_name,
        approved=False,
    )
    enforce(ctx)

    _ensure_kubeconfig_loaded()
    v1 = client.CoreV1Api()

    # bound tail_lines defensively
    if tail_lines is not None:
        if tail_lines < 1:
            raise InvalidRequest("tail_lines must be >= 1")
        if tail_lines > 2000:
            raise InvalidRequest("tail_lines too large (max 2000)")

    text = v1.read_namespaced_pod_log(
        name=pod_name,
        namespace=namespace,
        container=container,
        tail_lines=tail_lines,
        since_seconds=since_seconds,
        _preload_content=True,
    )
    return ("text/plain", text)
