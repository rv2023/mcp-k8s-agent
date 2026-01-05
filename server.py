from typing import List
import sys

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from tools_read import (
    k8s_list,
    k8s_get,
    k8s_list_events,
    k8s_pod_logs,
)
from tools_write import k8s_delete


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
            description="Delete a single namespaced Kubernetes resource (approval required)",
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


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "k8s_list":
        return [TextContent(type="text", text=await k8s_list(arguments))]

    if name == "k8s_get":
        return [TextContent(type="text", text=await k8s_get(arguments))]

    if name == "k8s_list_events":
        return [TextContent(type="text", text=await k8s_list_events(arguments))]

    if name == "k8s_pod_logs":
        return [TextContent(type="text", text=await k8s_pod_logs(arguments))]

    if name == "k8s_delete":
        return [TextContent(type="text", text=await k8s_delete(arguments))]

    raise ValueError(f"Unknown tool: {name}")


if __name__ == "__main__":
    import asyncio
    from mcp.server.stdio import stdio_server

    async def main():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream=read_stream,
                write_stream=write_stream,
                initialization_options={},
            )

    asyncio.run(main())