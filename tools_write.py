import json
from typing import Dict, Any

from kubernetes import client, config
from kubernetes.dynamic import DynamicClient

from gate import RequestContext, enforce


def _get_resource(dyn: DynamicClient, api_version: str, plural: str):
    """
    Get resource using API discovery.
    Works with kubernetes client v34.1.0+
    """
    try:
        for resource in dyn.resources.search(api_version=api_version):
            if resource.name == plural:
                return resource
    except Exception:
        pass

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


async def k8s_delete(arguments: Dict[str, Any]) -> str:
    namespace = arguments["namespace"]
    name = arguments["name"]
    group = arguments["group"]
    version = arguments["version"]
    plural = arguments["plural"]
    approved = arguments.get("approved", False)

    ctx = RequestContext(
        tool_name="k8s_delete",
        verb="delete",
        kind=arguments.get("kind"),
        namespace=namespace,
        name=name,
        approved=approved,
        arguments=arguments,
    )
    enforce(ctx)

    config.load_kube_config()
    dyn = DynamicClient(client.ApiClient())

    api_version = f"{group}/{version}" if group else version
    resource = _get_resource(dyn, api_version, plural)

    resp = resource.delete(name=name, namespace=namespace)

    return json.dumps(
        {
            "status": "deleted",
            "resource": plural,
            "name": name,
            "namespace": namespace,
            "raw": resp.to_dict() if hasattr(resp, "to_dict") else str(resp),
        },
        indent=2,
    )