from langchain_core.tools import StructuredTool, ToolException

def to_langchain_tool(client, mcp_tool) -> StructuredTool:
    async def call(**kwargs):
        result = await client.call_tool(mcp_tool.name, kwargs)
        text = "\n".join(block.text for block in result.content if block.type == "text")
        if result.is_error:
            raise ToolException(text)     # LangGraph turns this into an error result for the model
        return text

    return StructuredTool(
        name=mcp_tool.name,
        description=mcp_tool.description or "",
        args_schema=mcp_tool.input_schema,   # the JSON schema your server generated
        coroutine=call,                      # async tool
        handle_tool_error=True,
    )