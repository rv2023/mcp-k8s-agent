import json
from typing import Dict, Any

from kubernetes import client, config
from kubernetes.dynamic import DynamicClient

from gate import RequestContext, enforce


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

    resource = dyn.resources.get(
        api_version=f"{group}/{version}" if group else version,
        plural=plural,
    )

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