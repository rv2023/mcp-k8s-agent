import json
from typing import Dict, Any

from kubernetes import client, config
from kubernetes.dynamic import DynamicClient

from gate import RequestContext, enforce


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

    config.load_kube_config()
    dyn = DynamicClient(client.ApiClient())

    resource = dyn.resources.get(
        api_version=f"{group}/{version}" if group else version,
        plural=plural,
    )

    items = resource.get(namespace=namespace).to_dict()

    # IMPORTANT:
    # - no pruning
    # - no sanitization
    # - raw JSON only
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

    config.load_kube_config()
    dyn = DynamicClient(client.ApiClient())

    resource = dyn.resources.get(
        api_version=f"{group}/{version}" if group else version,
        plural=plural,
    )

    obj = resource.get(name=name, namespace=namespace).to_dict()

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

    # Logs are already plain text
    return logs