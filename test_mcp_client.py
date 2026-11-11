import asyncio
import sys
from pathlib import Path
from mcp import Client, StdioServerParameters

SERVER = Path(__file__).parent / "mcp_server.py"

async def main():
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)])
    async with Client(params) as client:
        tools = await client.list_tools()
        for tool in tools.tools:
            print(tool.name, "|", tool.description)
            print("   ", tool.input_schema)

        # 1. list_patients: no arguments
        result = await client.call_tool("list_patients", {})
        print("\nlist_patients is_error:", result.is_error)
        print(result.structured_content)

        # 2. get_conditions with a real id
        result = await client.call_tool("get_conditions",
                                        {"patient_id": "35888667-7e81-9343-2db6-3cfa9fa4e01b", "active_only": True})
        print("\nget_conditions is_error:", result.is_error)
        print(result.structured_content)

        # 3. get_conditions with a fake id
        result = await client.call_tool("get_conditions",
                                        {"patient_id": "123", "active_only": True})
        print("\nget_conditions is_error:", result.is_error)
        print(result.content[0].text)



asyncio.run(main())