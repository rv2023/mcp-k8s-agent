import asyncio

from mcp.client.stdio import stdio_client, StdioServerParameters, SessionMessage
from mcp.types import JSONRPCMessage


async def send(write_stream, msg: JSONRPCMessage):
    await write_stream.send(SessionMessage(msg))


async def recv(read_stream):
    sm = await read_stream.receive()
    if isinstance(sm, Exception):
        raise sm
    return sm.message.model_dump()


async def main():
    server = StdioServerParameters(
        command="python",
        args=["server.py"],
    )

    async with stdio_client(server) as (read_stream, write_stream):

        # 1️⃣ initialize
        await send(
            write_stream,
            JSONRPCMessage(
                jsonrpc="2.0",
                id=1,
                method="initialize",
                params={
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "phase2-smoke-test",
                        "version": "0.1",
                    },
                },
            ),
        )

        init_resp = await recv(read_stream)
        assert "result" in init_resp, init_resp

        # 2️⃣ initialized notification
        await send(
            write_stream,
            JSONRPCMessage(
                jsonrpc="2.0",
                method="notifications/initialized",
                params={},
            ),
        )

        # 3️⃣ list tools
        await send(
            write_stream,
            JSONRPCMessage(
                jsonrpc="2.0",
                id=2,
                method="tools/list",
            ),
        )

        tools_resp = await recv(read_stream)
        tool_names = [t["name"] for t in tools_resp["result"]["tools"]]

        assert "k8s_delete" in tool_names, tool_names

        # 4️⃣ delete without approval must fail
        await send(
            write_stream,
            JSONRPCMessage(
                jsonrpc="2.0",
                id=3,
                method="tools/call",
                params={
                    "name": "k8s_delete",
                    "arguments": {
                        "namespace": "default",
                        "group": "",
                        "version": "v1",
                        "plural": "pods",
                        "name": "does-not-matter",
                        "approved": False,
                    },
                },
            ),
        )

        delete_resp = await recv(read_stream)

        text = delete_resp["result"]["content"][0]["text"].lower()
        assert "blocked" in text or "approved=true" in text, delete_resp

        print("✅ Phase 2 smoke test passed")

asyncio.run(main())