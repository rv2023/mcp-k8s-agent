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