import sys
import asyncio

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

print("MCP k8s-agent server starting...", file=sys.stderr)

server = Server(
    name="mcp-k8s-agent",
    version="0.1.0",
)


@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="ping",
            description="Health check",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "ping":
        return [
            TextContent(
                type="text",
                text="pong - k8s-agent is working!",
            )
        ]

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