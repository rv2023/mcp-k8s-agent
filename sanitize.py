# sanitizer.py
import re
import math
from typing import Dict, Any

MAX_LINES = 500

REDACT_PATTERNS = [
    (re.compile(r'password\s*=\s*\S+', re.IGNORECASE), "password"),
    (re.compile(r'token\s*=\s*\S+', re.IGNORECASE), "token"),
    (re.compile(r'api[_-]?key\s*=\s*\S+', re.IGNORECASE), "api-key"),
    (re.compile(r'bearer\s+[a-zA-Z0-9\-_.]+', re.IGNORECASE), "bearer"),
    (re.compile(r'eyJ[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+'), "jwt"),
]

BASE64_RE = re.compile(r'[A-Za-z0-9+/=]{20,}')

def _entropy(s: str) -> float:
    probs = [s.count(c) / len(s) for c in set(s)]
    return -sum(p * math.log2(p) for p in probs)

def sanitize_output(tool_name: str, raw: str) -> str:
    text = raw

    # Pattern redaction
    for regex, label in REDACT_PATTERNS:
        text = regex.sub(f"[REDACTED: {label}]", text)

    # High entropy strings (base64 / secrets)
    def redact_entropy(match):
        val = match.group(0)
        if _entropy(val) > 4.0:
            return "[REDACTED: high-entropy]"
        return val

    text = BASE64_RE.sub(redact_entropy, text)

    # Truncate noisy outputs (logs)
    lines = text.splitlines()
    if len(lines) > MAX_LINES:
        lines = lines[:MAX_LINES]
        lines.append("\n[Output truncated]")

    return "\n".join(lines)


def prune_k8s_object(obj: Dict[str, Any]) -> Dict[str, Any]:
    """Structural pruning for Kubernetes API objects."""
    if not isinstance(obj, dict):
        return obj

    obj = dict(obj)

    kind = obj.get("kind")
    if kind == "Secret":
        obj["data"] = {k: "[REDACTED]" for k in obj.get("data", {})}
        obj["stringData"] = {k: "[REDACTED]" for k in obj.get("stringData", {})}

    return obj
