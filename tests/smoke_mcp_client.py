import asyncio

from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession


async def main():
    server = StdioServerParameters(
        command="python",
        args=["server.py"],
    )

    async with stdio_client(server) as (read_stream, write_stream):
        async with ClientSession(
            read_stream, 
            write_stream,
        ) as session:
            # 1️⃣ initialize
            result = await session.initialize()
            print(f"✅ Initialized: {result.serverInfo}")

            # 2️⃣ list tools
            tools_result = await session.list_tools()
            tool_names = [t.name for t in tools_result.tools]
            assert "k8s_delete" in tool_names, tool_names
            print(f"✅ Tools: {tool_names}")

            # 3️⃣ delete without approval must fail
            delete_result = await session.call_tool(
                "k8s_delete",
                arguments={
                    "namespace": "default",
                    "group": "",
                    "version": "v1",
                    "plural": "pods",
                    "name": "does-not-matter",
                    "approved": False,
                },
            )

            text = delete_result.content[0].text.lower()
            assert "approved" in text or "blocked" in text, text
            print(f"✅ Delete blocked as expected: {text[:100]}")

            print("✅ Smoke test passed")


if __name__ == "__main__":
    asyncio.run(main())