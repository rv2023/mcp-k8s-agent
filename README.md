# mcp-k8s-agent

A **Model Context Protocol (MCP) server** for safe, policy-gated Kubernetes operations.

## Features

- 🔍 **Read Operations** — List and get any namespaced Kubernetes resource (including CRDs)
- 📋 **Events & Logs** — View namespace events and pod logs for debugging
- 🗑️ **Controlled Deletes** — Delete resources with explicit approval gate
- 🛡️ **Safety First** — Policy enforcement in code, not prompts
- 🔌 **Dynamic Discovery** — No hardcoded resource types, uses K8s API discovery

## Tools

| Tool | Description |
|------|-------------|
| `k8s_list` | List namespaced resources |
| `k8s_get` | Get a single resource by name |
| `k8s_list_events` | List events in a namespace |
| `k8s_pod_logs` | Read logs from a pod |
| `k8s_delete` | Delete a resource (requires `approved=true`) |

## Installation

### Prerequisites

- Python 3.10+
- kubectl configured with cluster access
- A running Kubernetes cluster (local or remote)

### Setup

```bash
git clone https://github.com/rv2023/mcp-k8s-agent.git
cd mcp-k8s-agent
pip install -e .
```

## Configuration

### Claude Desktop

Add to your Claude Desktop config (`~/.config/claude/claude_desktop_config.json` on Linux or `%APPDATA%\Claude\claude_desktop_config.json` on Windows):

```json
{
  "mcpServers": {
    "k8s-agent": {
      "command": "python",
      "args": ["/path/to/mcp-k8s-agent/server.py"]
    }
  }
}
```

### Windows with WSL

```json
{
  "mcpServers": {
    "k8s-agent": {
      "command": "wsl",
      "args": ["python3", "/home/user/mcp-k8s-agent/server.py"]
    }
  }
}
```

## Usage Examples

Once configured, ask Claude:

```
"List all pods in the kube-system namespace"
"Get the deployment nginx in the default namespace"
"Show me events in the payments namespace"
"Get logs from pod my-app-xyz in production namespace"
"Delete pod crashed-pod in test namespace" (will require approval)
```

## Safety Model

### Enforced in Code

| Rule | Enforcement |
|------|-------------|
| No Secrets/ConfigMaps | Blocked by `gate.py` |
| Namespace required | All operations scoped |
| No bulk operations | Selectors blocked |
| Mutations need approval | `approved=true` required |
| One tool = one API call | No hidden fan-out |

### Forbidden by Design

- ❌ Reading Secrets or ConfigMaps
- ❌ Cluster-wide operations
- ❌ Selector-based bulk deletes
- ❌ Exec into pods
- ❌ Port forwarding

## Architecture

```
┌─────────────────┐     stdio/JSON-RPC     ┌─────────────────┐
│  Claude Desktop │ ◄──────────────────────► │   server.py     │
└─────────────────┘                         └────────┬────────┘
                                                     │
                                            ┌────────▼────────┐
                                            │    gate.py      │
                                            │  (policy gate)  │
                                            └────────┬────────┘
                                                     │
                              ┌───────────────┬──────┴──────┬───────────────┐
                              ▼               ▼              ▼               ▼
                        tools_read.py    tools_write.py  sanitize.py    K8s API
```

## Project Structure

```
mcp-k8s-agent/
├── server.py          # MCP server, tool registration
├── gate.py            # Policy enforcement (single entry point)
├── tools_read.py      # k8s_list, k8s_get, k8s_list_events, k8s_pod_logs
├── tools_write.py     # k8s_delete
├── sanitize.py        # Output pruning (managedFields removal)
├── tests/
│   └── smoke_mcp_client.py
├── docs/
│   └── ARCHITECTURE.md
├── pyproject.toml
└── README.md
```

## Testing

```bash
# Run smoke test
python tests/smoke_mcp_client.py

# Manual server test
python server.py
```

## Roadmap

- [x] Phase 1: Read operations (list, get, events, logs)
- [x] Phase 2: Delete with approval gate
- [ ] Phase 3: Sanitization (redact sensitive data in logs/env vars)
- [ ] Phase 4: `k8s_patch` for controlled mutations

## License

MIT

## Contributing

Issues and PRs welcome. Please ensure changes maintain the safety guarantees documented in [ARCHITECTURE.md](docs/ARCHITECTURE.md).
```

---

## Architecture Additions

Your `ARCHITECTURE.md` is already excellent. Consider adding these sections:

### 1. Add MCP SDK Version Note

```markdown
## 📦 Dependencies

- **MCP SDK**: `>=1.25.0` — Uses `InitializationOptions` with required `server_name`, `server_version`, `capabilities`
- **Kubernetes Client**: `>=29.0.0` — Uses `DynamicClient` for API discovery
```

### 2. Add Error Handling Section

```markdown
## 🚨 Error Handling

All tool invocations are wrapped in `_safe_call()` which:

1. Catches `GateError` → returns `"BLOCKED: {reason}"`
2. Catches other exceptions → returns `"ERROR: {type}: {message}"`
3. Never exposes stack traces to MCP clients

This ensures policy denials and runtime errors both return text content, not protocol-level errors.
```

### 3. Add Future Work Section

```markdown
## 🔮 Future Phases

### Phase 3: Information Safety
- Redact Secret `.data` values if accidentally exposed
- Scrub tokens/passwords from `env[].value` in pod specs
- Sanitize logs for JWTs, bearer tokens, API keys

### Phase 4: Controlled Mutations
- `k8s_patch` tool for:
  - Scaling deployments
  - Updating container images
  - Adding labels/annotations
- Requires `approved=true` like delete
```

---

## Minor Code Suggestions

1. **`sanitize.py`** — Currently minimal. For Phase 3, expand to:
   - Redact env vars matching password/token patterns
   - Redact Secret data fields
   - Scrub JWT patterns from logs

2. **Consider adding a `ping` tool** for health checks:
```python
Tool(
    name="ping",
    description="Health check",
    inputSchema={"type": "object", "properties": {}, "additionalProperties": False},
)
```

3. **Version constant** — Add to `server.py`:
```python
VERSION = "0.2.0"  # Keep in sync with pyproject.toml
```

---

Overall, the code is clean and well-structured. The safety model is solid. 🚀