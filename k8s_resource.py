import json
from typing import Optional
from kubernetes import client, config
from kubernetes.dynamic import DynamicClient


# Fallback: plural -> kind (covers built-ins + common resources)
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


def load_dynamic_client() -> DynamicClient:
    # Uses local kubeconfig (same as existing code)
    config.load_kube_config()
    return DynamicClient(client.ApiClient())


def api_version_of(group: str, version: str) -> str:
    return f"{group}/{version}" if group else version


def get_resource(dyn: DynamicClient, api_version: str, plural: str):
    """
    Resolve a Kubernetes resource via discovery.
    Works with kubernetes client v34.1.0+ (same as your existing helper).
    """
    # Try searching available resources
    try:
        for resource in dyn.resources.search(api_version=api_version):
            if resource.name == plural:
                return resource
    except Exception:
        pass

    # Fallback: kind lookup
    kind = PLURAL_TO_KIND.get(plural.lower())
    if kind:
        return dyn.resources.get(api_version=api_version, kind=kind)

    raise ValueError(f"Cannot resolve resource for plural='{plural}' api_version='{api_version}'")