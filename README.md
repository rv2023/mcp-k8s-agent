# mcp-k8s-agent

A **Model Context Protocol (MCP) server** that lets AI assistants (like Claude) safely interact with Kubernetes clusters.

## What is this?

This project creates a bridge between AI assistants and Kubernetes. Instead of giving an AI direct access to your cluster (dangerous!), this server acts as a **safety layer** that:

- ✅ Allows reading cluster state (pods, deployments, logs)
- ✅ Allows safe, controlled changes (scale, update image, restart)
- ❌ Blocks dangerous operations (secrets access, bulk deletes)
- ❌ Requires explicit approval for any changes

## Quick Example

Once configured, you can ask Claude:

```
"List all pods in the payments namespace"
"Why is the api deployment failing?"
"Scale the web deployment to 5 replicas"
"Update the nginx container image to nginx:1.25"
```

Claude uses this MCP server to safely execute these requests against your cluster.

---

## Features

### 🔍 Read Operations (Safe, No Approval Needed)

| Tool | What it does | Example |
|------|--------------|---------|
| `k8s_list` | List resources in a namespace | List all pods in `kube-system` |
| `k8s_get` | Get details of one resource | Get deployment `nginx` details |
| `k8s_list_events` | View namespace events | See what's happening in `production` |
| `k8s_pod_logs` | Read pod logs | Debug why a pod is crashing |

### ✏️ Write Operations (Require `approved=true`)

| Tool | What it does | Example |
|------|--------------|---------|
| `k8s_delete` | Delete one resource | Delete a stuck pod |
| `k8s_patch` | Make controlled changes | Scale, update image, restart |

### 🛡️ Safety Features

- **No Secrets Access** — Secrets and ConfigMaps are blocked
- **Namespace Required** — No cluster-wide operations
- **No Bulk Operations** — Can't delete multiple resources at once
- **Approval Required** — All changes need explicit `approved=true`
- **Intent-Based Patches** — Can't send arbitrary YAML, only specific actions
- **Output Sanitization** — Passwords and tokens are redacted

---

## Installation

### Prerequisites

- Python 3.10 or higher
- A Kubernetes cluster (local or remote)
- `kubectl` configured and working

### Step 1: Clone and Install

```bash
git clone https://github.com/rv2023/mcp-k8s-agent.git
cd mcp-k8s-agent
pip install -e .
```

### Step 2: Verify kubectl Works

```bash
kubectl get pods -A
```

If this works, the MCP server will work too (it uses the same config).

### Step 3: Test the Server

```bash
python tests/smoke_mcp_client.py
```

You should see:
```
✅ Initialized: ...
✅ Tools: ['k8s_list', 'k8s_get', 'k8s_list_events', 'k8s_pod_logs', 'k8s_delete', 'k8s_patch']
✅ Delete blocked as expected: ...
✅ Patch blocked as expected: ...
✅ Smoke test passed
```

---

## Configuration

### Claude Desktop (macOS/Linux)

Add to `~/.config/claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "k8s-agent": {
      "command": "python",
      "args": ["/full/path/to/mcp-k8s-agent/server.py"]
    }
  }
}
```

### Claude Desktop (Windows with WSL)

Add to `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "k8s-agent": {
      "command": "wsl",
      "args": ["python3", "/home/youruser/mcp-k8s-agent/server.py"]
    }
  }
}
```

Then restart Claude Desktop.

---

## Usage Examples

### Reading Cluster State

```
"List all deployments in the production namespace"
"Get the details of the api-server pod in staging"
"Show me the logs from the crashed payment-service pod"
"What events happened in the monitoring namespace?"
```

### Making Changes (Claude will ask for approval)

```
"Scale the web deployment to 3 replicas"
→ Claude will set approved=true after you confirm

"Update the api container image to myrepo/api:v2.0"
→ Claude will show you exactly what will change

"Restart the cache deployment to pick up the new config"
→ Triggers a rolling restart
```

---

## Available Patch Actions

The `k8s_patch` tool only accepts these specific actions:

### 1. Scale (change replica count)

**Works on:** Deployments, StatefulSets

```json
{
  "action": "scale",
  "replicas": 3
}
```

**Limits:** 0-100 replicas (configurable in gate.py)

### 2. Update Image (change container image)

**Works on:** Deployments, StatefulSets, DaemonSets

```json
{
  "action": "update_image",
  "container": "nginx",
  "image": "nginx:1.25"
}
```

### 3. Rollout Restart (restart all pods)

**Works on:** Deployments, StatefulSets, DaemonSets

```json
{
  "action": "rollout_restart"
}
```

**Why these three?** They cover 90% of "quick fix" scenarios without exposing dangerous capabilities.

---

## Project Structure

```
mcp-k8s-agent/
├── server.py          # MCP entry point - registers tools, handles requests
├── gate.py            # Safety policy - single source of allow/deny decisions
├── tools_read.py      # Read operations (list, get, events, logs)
├── tools_write.py     # Write operations (delete, patch)
├── sanitize.py        # Output cleaning (redact secrets, truncate logs)
├── k8s_resource.py    # Kubernetes API helper (resource discovery)
├── tests/
│   └── smoke_mcp_client.py
└── docs/
    └── ARCHITECTURE.md
```

### How a Request Flows

```
Claude asks: "Scale api to 5 replicas"
         ↓
    server.py receives request
         ↓
    gate.py checks: namespace? approved? valid action?
         ↓
    tools_write.py generates patch, calls K8s API
         ↓
    sanitize.py cleans the response
         ↓
    Claude receives: "Scaled Deployment default/api to 5 replicas"
```

---

## Security Model

### What's Blocked (and Why)

| Blocked | Reason |
|---------|--------|
| Secrets | Contains passwords, API keys |
| ConfigMaps | May contain sensitive config |
| Cluster-wide operations | Too much blast radius |
| Bulk deletes | Accidental mass deletion |
| Arbitrary patches | Could change anything |
| Selectors | Could match multiple resources |

### What's Allowed

| Allowed | Conditions |
|---------|------------|
| List/Get any resource | Must specify namespace |
| Pod logs | Must specify pod name |
| Delete one resource | Must have `approved=true` |
| Scale/Update/Restart | Must have `approved=true` + valid params |

### Defense in Depth

1. **Gate blocks bad requests** — Before any K8s API call
2. **Sanitization cleans outputs** — Redacts passwords, tokens, JWTs
3. **Kubernetes RBAC still applies** — Your kubeconfig permissions matter

---

## Troubleshooting

### "Cannot resolve resource" error

The server couldn't find the resource type. Check:
- Is `plural` spelled correctly? (`deployments` not `deployment`)
- Is the resource namespaced? (nodes and clusterroles aren't)

### "BLOCKED: Mutation requires approved=true"

This is working correctly! The server won't make changes without explicit approval.

### "Error loading kubeconfig"

Make sure `kubectl get pods` works from the same environment where the server runs.

### Server not appearing in Claude

1. Check the config path is correct
2. Restart Claude Desktop completely
3. Check server logs: `python server.py` should start without errors

---

## License

MIT

---

## Contributing

Issues and PRs welcome. Please read [ARCHITECTURE.md](docs/ARCHITECTURE.md) to understand the safety model before proposing changes.

**Important:** Any PR that weakens the safety guarantees will be rejected.