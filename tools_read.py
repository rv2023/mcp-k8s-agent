import json
from typing import Dict, Any

from kubernetes import client, config

from gate import RequestContext, enforce
from sanitize import prune_k8s_object
from k8s_resource import load_dynamic_client, api_version_of, get_resource


async def k8s_list(arguments: Dict[str, Any]) -> str:
    namespace = arguments["namespace"]
    group = arguments["group"]
    version = arguments["version"]
    plural = arguments["plural"]

    ctx = RequestContext(
        tool_name="k8s_list",
        verb="list",
        kind=arguments.get("kind"),
        namespace=namespace,
        arguments=arguments,
    )
    enforce(ctx)

    dyn = load_dynamic_client()
    api_version = api_version_of(group, version)
    resource = get_resource(dyn, api_version, plural)

    items = resource.get(namespace=namespace).to_dict()

    # Structural pruning only on object-shaped outputs
    if isinstance(items, dict) and isinstance(items.get("items"), list):
        pruned = dict(items)
        pruned["items"] = [prune_k8s_object(i) for i in items["items"]]
        items = pruned

    return json.dumps(items, indent=2, sort_keys=True)


async def k8s_get(arguments: Dict[str, Any]) -> str:
    namespace = arguments["namespace"]
    name = arguments["name"]
    group = arguments["group"]
    version = arguments["version"]
    plural = arguments["plural"]

    ctx = RequestContext(
        tool_name="k8s_get",
        verb="get",
        kind=arguments.get("kind"),
        namespace=namespace,
        name=name,
        arguments=arguments,
    )
    enforce(ctx)

    dyn = load_dynamic_client()
    api_version = api_version_of(group, version)
    resource = get_resource(dyn, api_version, plural)

    obj = resource.get(name=name, namespace=namespace).to_dict()

    # Structural pruning only on object-shaped outputs
    obj = prune_k8s_object(obj)

    return json.dumps(obj, indent=2, sort_keys=True)


async def k8s_list_events(arguments: Dict[str, Any]) -> str:
    namespace = arguments["namespace"]

    ctx = RequestContext(
        tool_name="k8s_list_events",
        verb="events",
        namespace=namespace,
        arguments=arguments,
    )
    enforce(ctx)

    config.load_kube_config()
    v1 = client.CoreV1Api()
    events = v1.list_namespaced_event(namespace=namespace).to_dict()
    return json.dumps(events, indent=2, sort_keys=True)


async def k8s_pod_logs(arguments: Dict[str, Any]) -> str:
    namespace = arguments["namespace"]
    pod = arguments["pod"]

    ctx = RequestContext(
        tool_name="k8s_pod_logs",
        verb="pod_logs",
        kind="Pod",
        namespace=namespace,
        name=pod,
        arguments=arguments,
    )
    enforce(ctx)

    config.load_kube_config()
    v1 = client.CoreV1Api()
    logs = v1.read_namespaced_pod_log(
        name=pod,
        namespace=namespace,
        container=arguments.get("container"),
        tail_lines=arguments.get("tail_lines"),
    )
    return logs
