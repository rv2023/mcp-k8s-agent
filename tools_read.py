import json
from typing import Dict, Any, Optional

from kubernetes import client, config
from kubernetes.dynamic import DynamicClient

from gate import RequestContext, enforce


def _get_resource(dyn: DynamicClient, api_version: str, plural: str):
    """
    Get resource using API discovery.
    Works with kubernetes client v34.1.0+
    """
    # Try searching available resources
    try:
        for resource in dyn.resources.search(api_version=api_version):
            if resource.name == plural:
                return resource
    except Exception:
        pass

    # Fallback: use kind lookup
    PLURAL_TO_KIND = {
        "pods": "Pod",
        "services": "Service",
        "deployments": "Deployment",
        "replicasets": "ReplicaSet",
        "daemonsets": "DaemonSet",
        "statefulsets": "StatefulSet",
        "configmaps": "ConfigMap",
        "secrets": "Secret",
        "serviceaccounts": "ServiceAccount",
        "namespaces": "Namespace",
        "nodes": "Node",
        "persistentvolumes": "PersistentVolume",
        "persistentvolumeclaims": "PersistentVolumeClaim",
        "events": "Event",
        "ingresses": "Ingress",
        "jobs": "Job",
        "cronjobs": "CronJob",
        "roles": "Role",
        "rolebindings": "RoleBinding",
        "clusterroles": "ClusterRole",
        "clusterrolebindings": "ClusterRoleBinding",
        "networkpolicies": "NetworkPolicy",
        "leases": "Lease",
        "horizontalpodautoscalers": "HorizontalPodAutoscaler",
        "poddisruptionbudgets": "PodDisruptionBudget",
        "resourcequotas": "ResourceQuota",
        "limitranges": "LimitRange",
        "endpoints": "Endpoints",
        "endpointslices": "EndpointSlice",
    }

    kind = PLURAL_TO_KIND.get(plural.lower())
    if kind:
        return dyn.resources.get(api_version=api_version, kind=kind)

    raise ValueError(f"Cannot resolve resource for plural='{plural}' api_version='{api_version}'")


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

    api_version = f"{group}/{version}" if group else version
    resource = _get_resource(dyn, api_version, plural)

    items = resource.get(namespace=namespace).to_dict()
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

    api_version = f"{group}/{version}" if group else version
    resource = _get_resource(dyn, api_version, plural)

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
    return logs