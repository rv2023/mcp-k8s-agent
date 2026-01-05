from typing import List
import logging

from sanitize import sanitize_output
from mcp.server import Server, InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from tools_read import k8s_list, k8s_get, k8s_list_events, k8s_pod_logs
from tools_write import k8s_delete, k8s_patch
from gate import GateError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-k8s-agent")

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
                "required": ["namespace", "name", "group", "version", "plural", "approved"],
                "additionalProperties": False,
            },
        ),
        Tool(
            name="k8s_patch",
            description="Intent-only, policy-gated patch for safe mutations. Requires approved=true.",
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
                    "action": {"type": "string", "enum": ["scale", "update_image", "rollout_restart"]},
                    "replicas": {"type": "integer"},
                    "container": {"type": "string"},
                    "image": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["namespace", "name", "group", "version", "plural", "approved", "action"],
                "additionalProperties": False,
            },
        ),
    ]


async def _safe_call(coro):
    try:
        return await coro
    except GateError as e:
        return f"BLOCKED: {e}"
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "k8s_list":
        raw = await _safe_call(k8s_list(arguments))
    elif name == "k8s_get":
        raw = await _safe_call(k8s_get(arguments))
    elif name == "k8s_list_events":
        raw = await _safe_call(k8s_list_events(arguments))
    elif name == "k8s_pod_logs":
        raw = await _safe_call(k8s_pod_logs(arguments))
    elif name == "k8s_delete":
        raw = await _safe_call(k8s_delete(arguments))
    elif name == "k8s_patch":
        raw = await _safe_call(k8s_patch(arguments))
    else:
        raise ValueError(f"Unknown tool: {name}")

    safe = sanitize_output(tool_name=name, raw=raw)
    return [TextContent(type="text", text=safe)]


if __name__ == "__main__":
    import asyncio
    from mcp.types import ServerCapabilities

    async def main():
        logger.info(
            "mcp-k8s-agent started | Phase 4 enabled | "
            "sanitized outputs, bounded logs, approval-gated writes, intent-only patches"
        )
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream=read_stream,
                write_stream=write_stream,
                initialization_options=InitializationOptions(
                    server_name="mcp-k8s-agent",
                    server_version="0.2.0",
                    capabilities=ServerCapabilities(tools={}),
                ),
            )

    asyncio.run(main())