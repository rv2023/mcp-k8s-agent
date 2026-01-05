from typing import List

from mcp.server import Server, InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from tools_read import (
    k8s_list,
    k8s_get,
    k8s_list_events,
    k8s_pod_logs,
)
from tools_write import k8s_delete
from gate import GateError


server = Server("mcp-k8s-agent")


@server.list_tools()
async def list_tools() -> List[Tool]:
    return [
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
                    "kind": {"type": "string"},
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
                    "name": {"type": "string"},
                    "group": {"type": "string"},
                    "version": {"type": "string"},
                    "plural": {"type": "string"},
                    "kind": {"type": "string"},
                },
                "required": ["namespace", "name", "group", "version", "plural"],
                "additionalProperties": False,
            },
        ),
        Tool(
            name="k8s_list_events",
            description="List namespaced Kubernetes events",
            inputSchema={
                "type": "object",
                "properties": {
                    "namespace": {"type": "string"},
                },
                "required": ["namespace"],
                "additionalProperties": False,
            },
        ),
        Tool(
            name="k8s_pod_logs",
            description="Read pod logs from a namespaced pod",
            inputSchema={
                "type": "object",
                "properties": {
                    "namespace": {"type": "string"},
                    "pod": {"type": "string"},
                    "container": {"type": "string"},
                    "tail_lines": {"type": "integer"},
                },
                "required": ["namespace", "pod"],
                "additionalProperties": False,
            },
        ),
        Tool(
            name="k8s_delete",
            description="Delete exactly one namespaced Kubernetes resource. Requires approved=true.",
            inputSchema={
                "type": "object",
                "properties": {
                    "namespace": {"type": "string"},
                    "name": {"type": "string"},
                    "group": {"type": "string"},
                    "version": {"type": "string"},
                    "plural": {"type": "string"},
                    "kind": {"type": "string"},
                    "approved": {"type": "boolean"},
                },
                "required": [
                    "namespace",
                    "name",
                    "group",
                    "version",
                    "plural",
                    "approved",
                ],
                "additionalProperties": False,
            },
        ),
    ]


async def _safe_call(coro):
    """Wrap tool calls to catch GateError and return as text."""
    try:
        return await coro
    except GateError as e:
        return f"BLOCKED: {e}"
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "k8s_list":
        result = await _safe_call(k8s_list(arguments))
        return [TextContent(type="text", text=result)]

    if name == "k8s_get":
        result = await _safe_call(k8s_get(arguments))
        return [TextContent(type="text", text=result)]

    if name == "k8s_list_events":
        result = await _safe_call(k8s_list_events(arguments))
        return [TextContent(type="text", text=result)]

    if name == "k8s_pod_logs":
        result = await _safe_call(k8s_pod_logs(arguments))
        return [TextContent(type="text", text=result)]

    if name == "k8s_delete":
        result = await _safe_call(k8s_delete(arguments))
        return [TextContent(type="text", text=result)]

    raise ValueError(f"Unknown tool: {name}")


if __name__ == "__main__":
    import asyncio
    from mcp.types import ServerCapabilities

    async def main():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream=read_stream,
                write_stream=write_stream,
                initialization_options=InitializationOptions(
                    server_name="mcp-k8s-agent",
                    server_version="0.1.0",
                    capabilities=ServerCapabilities(tools={}),
                ),
            )

    asyncio.run(main())