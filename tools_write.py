import json
from typing import Dict, Any
from datetime import datetime, timezone

from gate import RequestContext, enforce
from k8s_resource import load_dynamic_client, api_version_of, get_resource


def _kind_for_plural(plural: str) -> str:
    p = plural.lower()
    if p == "deployments":
        return "Deployment"
    if p == "statefulsets":
        return "StatefulSet"
    if p == "daemonsets":
        return "DaemonSet"
    return plural  # fallback (shouldn't be used for patch allowlist)


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

    dyn = load_dynamic_client()
    api_version = api_version_of(group, version)
    resource = get_resource(dyn, api_version, plural)

    resource.delete(name=name, namespace=namespace)

    # Minimal response (no raw object dumps)
    return json.dumps(
        {
            "result": "deleted",
            "target": {
                "namespace": namespace,
                "group": group,
                "version": version,
                "plural": plural,
                "name": name,
            },
            "explain": f"Deleted {plural} {namespace}/{name}.",
        },
        indent=2,
    )


async def k8s_patch(arguments: Dict[str, Any]) -> str:
    namespace = arguments["namespace"]
    name = arguments["name"]
    group = arguments["group"]
    version = arguments["version"]
    plural = arguments["plural"]
    approved = arguments.get("approved", False)

    action = arguments.get("action")

    ctx = RequestContext(
        tool_name="k8s_patch",
        verb="patch",
        kind=arguments.get("kind"),
        namespace=namespace,
        name=name,
        approved=approved,
        arguments=arguments,
    )
    enforce(ctx)

    dyn = load_dynamic_client()
    api_version = api_version_of(group, version)
    resource = get_resource(dyn, api_version, plural)

    kind = _kind_for_plural(plural)

    if action == "scale":
        replicas = arguments["replicas"]
        patch = {"spec": {"replicas": replicas}}
        explain = f"Scaled {kind} {namespace}/{name} to {replicas} replicas."

    elif action == "update_image":
        container = arguments["container"]
        image = arguments["image"]
        patch = {
            "spec": {
                "template": {
                    "spec": {
                        "containers": [
                            {"name": container, "image": image},
                        ]
                    }
                }
            }
        }
        explain = f"Updated image for container {container} in {kind} {namespace}/{name} to {image}."

    elif action == "rollout_restart":
        # Standard key understood by tooling
        ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        patch = {
            "spec": {
                "template": {
                    "metadata": {
                        "annotations": {
                            "kubectl.kubernetes.io/restartedAt": ts
                        }
                    }
                }
            }
        }
        explain = f"Triggered rollout restart for {kind} {namespace}/{name}."

    else:
        # Gate should have blocked unknown actions; keep fail-closed anyway
        raise ValueError(f"Unsupported action: {action}")

    # Apply patch using strategic merge patch content type
    resource.patch(
        name=name,
        namespace=namespace,
        body=patch,
        content_type="application/strategic-merge-patch+json",
    )

    # Minimal response (no objects, no patch echo)
    out = {
        "result": "patched",
        "action": action,
        "target": {
            "kind": kind,
            "namespace": namespace,
            "group": group,
            "version": version,
            "plural": plural,
            "name": name,
        },
        "explain": explain,
    }

    # Add action-specific fields (small, auditable)
    if action == "scale":
        out["replicas"] = arguments["replicas"]
    elif action == "update_image":
        out["container"] = arguments["container"]
        out["image"] = arguments["image"]

    return json.dumps(out, indent=2)
