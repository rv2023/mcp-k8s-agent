from typing import Any, Dict


def prune_k8s_object(obj: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministic pruning only.
    Removes noisy / non-essential fields.
    """

    if not isinstance(obj, dict):
        return obj

    meta = obj.get("metadata")
    if isinstance(meta, dict):
        meta.pop("managedFields", None)

    return obj