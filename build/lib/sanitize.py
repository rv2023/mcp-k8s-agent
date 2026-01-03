# sanitize.py
from __future__ import annotations

from typing import Any, Dict


def prune_k8s_object(obj: Dict[str, Any]) -> Dict[str, Any]:
    """
    Keep responses readable and reduce noise.
    Deterministic, no "smart" behavior.

    We intentionally remove:
    - managedFields (very large)
    """
    if not isinstance(obj, dict):
        return {"value": obj}

    out = dict(obj)

    md = out.get("metadata")
    if isinstance(md, dict) and "managedFields" in md:
        md = dict(md)
        md.pop("managedFields", None)
        out["metadata"] = md

    return out
