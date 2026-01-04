from __future__ import annotations

import json
from typing import Any, Dict

from kubernetes import client, config
from kubernetes.dynamic import DynamicClient

from gate import RequestContext, enforce
from sanitize import prune_k8s_object
from gate import enforce, RequestContext



def _load_dynamic() -> DynamicClient:
    config.load_kube_config()
    api_client = client.ApiClient()
    return DynamicClient(api_client)


def _api_version(group: str, version: str) -> str:
    group = (group or "").strip()
    version = (version or "").strip()
    return version if group == "" else f"{group}/{version}"


async def k8s_list(arguments: Dict[str, Any]) -> str:
    namespace = (arguments.get("namespace") or "").strip()
    group = (arguments.get("group") or "").strip()
    version = (arguments.get("version") or "").strip()
    plural = (arguments.get("plural") or "").strip()
    kind = arguments.get("kind")

    ctx = RequestContext(
        tool_name="k8s_list",
        verb="list",
        kind=kind,
        namespace=namespace,
        name=None,
        approved=False,
    )
    enforce(ctx, arguments=arguments)

    dyn = _load_dynamic()
    api_version = _api_version(group, version)
    resource = dyn.resources.get(api_version=api_version, plural=plural)

    limit = arguments.get("limit")
    resp = resource.get(namespace=namespace, limit=limit) if limit else resource.get(namespace=namespace)

    raw = resp.to_dict() if hasattr(resp, "to_dict") else resp
    out = prune_k8s_object(raw if isinstance(raw, dict) else {"value": raw})
    return json.dumps(out, indent=2, sort_keys=True)


async def k8s_get(arguments: Dict[str, Any]) -> str:
    namespace = (arguments.get("namespace") or "").strip()
    group = (arguments.get("group") or "").strip()
    version = (arguments.get("version") or "").strip()
    plural = (arguments.get("plural") or "").strip()
    name = (arguments.get("name") or "").strip()
    kind = arguments.get("kind")

    ctx = RequestContext(
        tool_name="k8s_get",
        verb="get",
        kind=kind,
        namespace=namespace,
        name=name,
        approved=False,
    )
    enforce(ctx, arguments=arguments)

    dyn = _load_dynamic()
    api_version = _api_version(group, version)
    resource = dyn.resources.get(api_version=api_version, plural=plural)

    resp = resource.get(name=name, namespace=namespace)
    raw = resp.to_dict() if hasattr(resp, "to_dict") else resp
    out = prune_k8s_object(raw if isinstance(raw, dict) else {"value": raw})
    return json.dumps(out, indent=2, sort_keys=True)


async def k8s_list_events(arguments: dict) -> str:
    namespace = arguments["namespace"]

    ctx = RequestContext(
        tool_name="k8s_events",
        verb="events",
        kind=None,
        namespace=namespace,
        name=None,
        approved=False,
    )

    enforce(ctx, arguments)

    # --- existing logic below ---
    v1 = client.CoreV1Api()
    events = v1.list_namespaced_event(
        namespace=namespace,
        limit=arguments.get("limit"),
    )

    return json.dumps(events.to_dict(), indent=2)

async def k8s_pod_logs(arguments: dict) -> str:
    namespace = arguments["namespace"]
    pod = arguments["pod"]

    ctx = RequestContext(
        tool_name="k8s_pod_logs",
        verb="pod_logs",
        kind="Pod",
        namespace=namespace,
        name=pod,
        approved=False,
    )

    enforce(ctx, arguments)

    # --- existing logic below ---
    v1 = client.CoreV1Api()
    logs = v1.read_namespaced_pod_log(
        name=pod,
        namespace=namespace,
        container=arguments.get("container"),
        tail_lines=arguments.get("tail_lines"),
    )

    return logs