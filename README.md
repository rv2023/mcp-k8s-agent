# MCP K8s Agent

A Model Context Protocol (MCP) server for Kubernetes cluster management via Claude.

## Features
- 🔍 List/Get any Kubernetes resource (including CRDs)
- 🗑️ Delete resources with approval confirmation
- 🔄 Dynamic API discovery (no hardcoded resource types)

## Installation

### Prerequisites
- Python 3.10+
- kubectl configured with cluster access

### Setup
pip install -e .

### Claude Desktop Configuration
Add to `claude_desktop_config.json`:
{
  "mcpServers": {
    "k8s-agent": {
      "command": "python",
      "args": ["/path/to/server.py"]
    }
  }
}

## Usage Examples
- "List all pods in the payments namespace"
- "Get the deployment nginx in default namespace"
- "Delete pod my-pod in test namespace"

## Tools
| Tool | Description |
|------|-------------|
| ping | Health check |
| k8s_list | List namespaced resources |
| k8s_get | Get single resource |
| k8s_delete | Delete resource (requires approval) |
```

---

## 🚀 **Feature Additions**

| Priority | Feature | Description |
|----------|---------|-------------|
| **High** | `k8s_apply` | Create/update resources from YAML |
| **High** | `k8s_patch` | Patch existing resources (fix image, scale, etc.) |
| **Medium** | `k8s_logs` | Get pod logs |
| **Medium** | `k8s_exec` | Execute commands in pods |
| **Medium** | `k8s_describe` | Get events + status (like kubectl describe) |
| **Low** | `k8s_port_forward` | Port forwarding |
| **Low** | `k8s_watch` | Watch for resource changes |

---

## 📦 **Project Structure**

Consider reorganizing:
```
mcp-k8s-agent/
├── src/
│   └── mcp_k8s_agent/
│       ├── __init__.py
│       ├── server.py
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── read.py
│       │   └── write.py
│       └── utils/
│           ├── sanitize.py
│           └── gate.py
├── tests/
│   ├── test_read.py
│   └── test_write.py
├── docs/
│   ├── ARCHITECTURE.md
│   └── DESIGN.md
├── .gitignore
├── LICENSE
├── README.md
└── pyproject.toml


Note:
- `plural` is always required and is resolved via Kubernetes API discovery
- `kind` is optional and never required for correctness