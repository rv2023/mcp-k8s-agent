# import asyncio
# import sys
# from typing import Any, Dict, List

# from mcp.server import Server
# from mcp.server.stdio import stdio_server
# from mcp.types import Tool, TextContent

# from tools_read import (
#     k8s_get,
#     k8s_list,
#     k8s_list_events,
#     k8s_pod_logs,
# )
# from tools_write import k8s_delete


# print("MCP k8s-agent server starting...", file=sys.stderr)

# # ✅ DO NOT pass protocol_version here
# server = Server(
#     name="mcp-k8s-agent",
#     version="0.2.0",
# )

# # -------------------------
# # Tool schemas
# # -------------------------

# PING_SCHEMA: Dict[str, Any] = {"type": "object", "properties": {}}

# K8S_LIST_SCHEMA: Dict[str, Any] = {
#     "type": "object",
#     "properties": {
#         "namespace": {"type": "string"},
#         "group": {"type": "string"},
#         "version": {"type": "string"},
#         "plural": {"type": "string"},
#         "kind": {"type": "string"},
#         "limit": {"type": "integer", "minimum": 1, "maximum": 500},
#     },
#     "required": ["namespace", "group", "version", "plural"],
#     "additionalProperties": False,
# }

# K8S_GET_SCHEMA: Dict[str, Any] = {
#     "type": "object",
#     "properties": {
#         "namespace": {"type": "string"},
#         "group": {"type": "string"},
#         "version": {"type": "string"},
#         "plural": {"type": "string"},
#         "kind": {"type": "string"},
#         "name": {"type": "string"},
#     },
#     "required": ["namespace", "group", "version", "plural", "name"],
#     "additionalProperties": False,
# }

# K8S_EVENTS_SCHEMA: Dict[str, Any] = {
#     "type": "object",
#     "properties": {
#         "namespace": {"type": "string"},
#         "limit": {"type": "integer", "minimum": 1, "maximum": 500},
#     },
#     "required": ["namespace"],
#     "additionalProperties": False,
# }

# K8S_POD_LOGS_SCHEMA: Dict[str, Any] = {
#     "type": "object",
#     "properties": {
#         "namespace": {"type": "string"},
#         "pod": {"type": "string"},
#         "container": {"type": "string"},
#         "tail_lines": {"type": "integer", "minimum": 1, "maximum": 5000},
#     },
#     "required": ["namespace", "pod"],
#     "additionalProperties": False,
# }

# K8S_DELETE_SCHEMA: Dict[str, Any] = {
#     "type": "object",
#     "properties": {
#         "namespace": {"type": "string"},
#         "group": {"type": "string"},
#         "version": {"type": "string"},
#         "plural": {"type": "string"},
#         "kind": {"type": "string"},
#         "name": {"type": "string"},
#         "approved": {"type": "boolean"},
#         "grace_period_seconds": {"type": "integer", "minimum": 0, "maximum": 3600},
#         "propagation_policy": {
#             "type": "string",
#             "enum": ["Foreground", "Background", "Orphan"],
#         },
#     },
#     "required": ["namespace", "group", "version", "plural", "name", "approved"],
#     "additionalProperties": False,
# }

# # -------------------------
# # Tool registration
# # -------------------------

# @server.list_tools()
# async def list_tools() -> List[Tool]:
#     return [
#         Tool(name="ping", description="Health check", inputSchema=PING_SCHEMA),
#         Tool(name="k8s_list", description="List resources", inputSchema=K8S_LIST_SCHEMA),
#         Tool(name="k8s_get", description="Get resource", inputSchema=K8S_GET_SCHEMA),
#         Tool(name="k8s_events", description="List events", inputSchema=K8S_EVENTS_SCHEMA),
#         Tool(name="k8s_pod_logs", description="Read pod logs", inputSchema=K8S_POD_LOGS_SCHEMA),
#         Tool(name="k8s_delete", description="Delete one resource", inputSchema=K8S_DELETE_SCHEMA),
#     ]


# @server.call_tool()
# async def call_tool(name: str, arguments: dict):
#     if name == "ping":
#         return [TextContent(type="text", text="pong")]

#     if name == "k8s_list":
#         return [TextContent(type="text", text=await k8s_list(arguments))]

#     if name == "k8s_get":
#         return [TextContent(type="text", text=await k8s_get(arguments))]

#     if name == "k8s_events":
#         return [TextContent(type="text", text=await k8s_list_events(arguments))]

#     if name == "k8s_pod_logs":
#         return [TextContent(type="text", text=await k8s_pod_logs(arguments))]

#     if name == "k8s_delete":
#         return [TextContent(type="text", text=await k8s_delete(arguments))]

#     raise ValueError(f"Unknown tool: {name}")


# async def main():
#     async with stdio_server() as (read_stream, write_stream):
#         await server.run(
#             read_stream=read_stream,
#             write_stream=write_stream,
#             initialization_options=server.create_initialization_options(),
#         )

# if __name__ == "__main__":
#     asyncio.run(main())

import asyncio
import sys
from typing import Any, Dict, List
from tools_read import k8s_list, k8s_get

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from tools_read import (
    k8s_get,
    k8s_list,
    k8s_list_events,
    k8s_pod_logs,
)
from tools_write import k8s_delete


print("MCP k8s-agent server starting...", file=sys.stderr)

server = Server(
    name="mcp-k8s-agent",
    version="0.2.0",
)

PING_SCHEMA: Dict[str, Any] = {"type": "object", "properties": {}}

@server.list_tools()
async def list_tools() -> List[Tool]:
    return [
        Tool(
            name="ping",
            description="Health check",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="k8s_delete",
            description="Delete exactly one namespaced Kubernetes resource. Requires approved=true.",
            inputSchema={
                "type": "object",
                "properties": {
                    "namespace": {"type": "string"},
                    "group": {"type": "string"},
                    "version": {"type": "string"},
                    "plural": {"type": "string"},
                    "name": {"type": "string"},
                    "approved": {"type": "boolean"},
                },
                "required": ["namespace", "group", "version", "plural", "name", "approved"],
                "additionalProperties": False,
            },
        ),
        Tool(
            name="k8s_list",
            description="List namespaced Kubernetes resources (read-only)",
            inputSchema={
                "type": "object",
                "properties": {
                    "namespace": {"type": "string"},
                    "group": {"type": "string"},
                    "version": {"type": "string"},
                    "plural": {"type": "string"},
                },
                "required": ["namespace", "group", "version", "plural"],
                "additionalProperties": False,
            },
        ),
        Tool(
            name="k8s_get",
            description="Get a single namespaced Kubernetes resource (read-only)",
            inputSchema={
                "type": "object",
                "properties": {
                    "namespace": {"type": "string"},
                    "group": {"type": "string"},
                    "version": {"type": "string"},
                    "plural": {"type": "string"},
                    "name": {"type": "string"},
                },
                "required": ["namespace", "group", "version", "plural", "name"],
                "additionalProperties": False,
            },
        ),
    ]



@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "ping":
        return [TextContent(type="text", text="pong")]

    if name == "k8s_list":
        out = await k8s_list(arguments)
        return [TextContent(type="text", text=out)]

    if name == "k8s_get":
        out = await k8s_get(arguments)
        return [TextContent(type="text", text=out)]

    if name == "k8s_delete":
        out = await k8s_delete(arguments)
        return [TextContent(type="text", text=out)]

    raise ValueError(f"Unknown tool: {name}")



async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream=read_stream,
            write_stream=write_stream,
            initialization_options=server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())