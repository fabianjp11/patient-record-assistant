import asyncio
import sys
from pathlib import Path

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.prebuilt import ToolNode, tools_condition
from mcp import Client, StdioServerParameters

from agent_raw import SYSTEM_PROMPT
from mcp_tools import to_langchain_tool

SERVER = Path(__file__).parent / "mcp_server.py"

async def main():
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)])
    async with Client(params) as client:         # the server stays open while the agent runs
        listed = await client.list_tools()
        tools = [to_langchain_tool(client, t) for t in listed.tools]

        llm = ChatAnthropic(model="claude-opus-5-5").bind_tools(tools)   # reads ANTHROPIC_API_KEY

        async def agent(state: MessagesState):
            response = await llm.ainvoke([SystemMessage(SYSTEM_PROMPT)] + state["messages"])
            return {"messages": [response]}      # LangGraph APPENDS it to the state

        graph = StateGraph(MessagesState)
        graph.add_node("agent", agent)
        graph.add_node("tools", ToolNode(tools))
        graph.add_edge(START, "agent")
        graph.add_conditional_edges("agent", tools_condition)   # tool_calls → "tools", otherwise → END
        graph.add_edge("tools", "agent")
        app = graph.compile(checkpointer=InMemorySaver())

        config = {"configurable": {"thread_id": "session-1"}}
        while True:
            question = input("\nYou: ")
            if not question.strip():
                continue
            if question in ("exit", "quit"):
                break

            async for update in app.astream({"messages": [("user", question)]}, config, stream_mode="updates"):
                for node_name, data in update.items():
                    for message in data["messages"]:
                        if node_name == "agent":
                            if message.tool_calls:
                                for call in message.tool_calls:
                                    print(f"-> {call['name']} {call['args']}")
                            else:
                                print("Claude:", message.text)
                        elif node_name == "tools":
                            print("   (tool result received)")


if __name__ == "__main__":
    asyncio.run(main())