# server.py
from __future__ import annotations

import asyncio
import sys
from typing import Any, Dict, List

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

import tools_read


print("MCP k8s-agent server starting...", file=sys.stderr)

server = Server(
    name="mcp-k8s-agent",
    version="0.1.0",
)


def _tool_schema_list_resources() -> Dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "namespace": {"type": "string"},
            "group": {"type": "string"},
            "version": {"type": "string"},
            "plural": {"type": "string"},
            "kind": {"type": ["string", "null"]},
        },
        "required": ["namespace", "group", "version", "plural"],
        "additionalProperties": False,
    }


def _tool_schema_get_resource() -> Dict[str, Any]:
    s = _tool_schema_list_resources()
    s["properties"]["name"] = {"type": "string"}
    s["required"] = ["namespace", "group", "version", "plural", "name"]
    return s


def _tool_schema_get_resource_status() -> Dict[str, Any]:
    return _tool_schema_get_resource()


def _tool_schema_list_events() -> Dict[str, Any]:
    return {
        "type": "object",
        "properties": {"namespace": {"type": "string"}},
        "required": ["namespace"],
        "additionalProperties": False,
    }


def _tool_schema_get_pod_logs() -> Dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "namespace": {"type": "string"},
            "pod_name": {"type": "string"},
            "container": {"type": ["string", "null"]},
            "tail_lines": {"type": ["integer", "null"]},
            "since_seconds": {"type": ["integer", "null"]},
        },
        "required": ["namespace", "pod_name"],
        "additionalProperties": False,
    }


@server.list_tools()
async def list_tools() -> List[Tool]:
    return [
        Tool(name="ping", description="Health check", inputSchema={"type": "object", "properties": {}, "additionalProperties": False}),
        Tool(name="list_resources", description="List resources in a namespace (any kind except forbidden).", inputSchema=_tool_schema_list_resources()),
        Tool(name="get_resource", description="Get a single resource by name (any kind except forbidden).", inputSchema=_tool_schema_get_resource()),
        Tool(name="get_resource_status", description="Get status subresource for a resource (if supported).", inputSchema=_tool_schema_get_resource_status()),
        Tool(name="list_events", description="List events in a namespace.", inputSchema=_tool_schema_list_events()),
        Tool(name="get_pod_logs", description="Get logs for one pod (namespaced).", inputSchema=_tool_schema_get_pod_logs()),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "ping":
        return [TextContent(type="text", text="pong - k8s-agent is working!")]

    args = arguments or {}

    try:
        if name == "list_resources":
            ctype, text = tools_read.list_resources(**args)
        elif name == "get_resource":
            ctype, text = tools_read.get_resource(**args)
        elif name == "get_resource_status":
            ctype, text = tools_read.get_resource_status(**args)
        elif name == "list_events":
            ctype, text = tools_read.list_events(**args)
        elif name == "get_pod_logs":
            ctype, text = tools_read.get_pod_logs(**args)
        else:
            raise ValueError(f"Unknown tool: {name}")

        # MCP TextContent is plain text; we embed JSON/text as a string.
        return [TextContent(type="text", text=text)]

    except Exception as e:
        # Deterministic error surface: return a readable string.
        # (We can tighten error typing later in Phase 4 audit work.)
        return [TextContent(type="text", text=f"ERROR: {type(e).__name__}: {e}")]


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream=read_stream,
            write_stream=write_stream,
            initialization_options=server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())