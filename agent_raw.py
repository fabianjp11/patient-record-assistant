import json
from datetime import date
import anthropic
import fhir_store

client = anthropic.Anthropic() # reads ANTHROPIC_API_KEY from the environment
MODEL = "claude-opus-5-5"

TOOLS = [
    {
        "name": "list_patients",
        "description": "List all patients with id, name, gender and birth date. "
                       "Use this first to find a patient's id from their name.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_conditions",
        "description": "Returns the list of conditions for a patient: condition, status, onset and resolved. "
                        "Use this to find a patient's conditions by Id",
        "input_schema": {
            "type": "object",
            "properties": {
                "patient_id":  {"type": "string",  "description": "The patient's id, as returned by list_patients"},
                "active_only": {"type": "boolean", "description": "If true, return only conditions with status 'active'"},
            },
            "required": ["patient_id"],
        },
    },
]

SYSTEM_PROMPT = f"""You are an assistant that answers questions about patient records. 
Today's date is {date.today().isoformat()}. 
Answer only from what the tools return, and say so when the data isn't there. 
Report the record without diagnosing or giving medical advice.
Keep answers short unless the user asks for detail.
"""

def run_tool(name: str, args: dict) -> str:
    if name == "list_patients":
        result = fhir_store.list_patients()
    elif name == "get_conditions":
        result = fhir_store.get_conditions(args["patient_id"], args.get("active_only", False))
    else:
        raise ValueError(f"Unknown tool: {name}")
    return json.dumps(result)


def ask(question: str, max_turns: int = 10) -> str:
    messages = [{"role": "user", "content": question}]

    for turn in range(max_turns):
        response = client.messages.create(model=MODEL, max_tokens=4096, tools=TOOLS, messages=messages, system=SYSTEM_PROMPT)

        if response.stop_reason == "end_turn":
            return "".join(block.text for block in response.content if block.type == "text")

        if response.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": response.content})
            continue

        if response.stop_reason != "tool_use":
            raise RuntimeError(f"Unexpected stop_reason: {response.stop_reason}")

        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"-> {block.name} {block.input}")
                try:
                    output = run_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": output,
                    })
                except Exception as exc:
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": f"Error: {exc}",
                        "is_error": True,
                    })

        messages.append({"role": "user", "content": tool_results})


    raise RuntimeError("Too many turns, possible loop")

if __name__ == "__main__":
    import sys
    question = " ".join(sys.argv[1:]) or "Which patients do we have?"
    print(ask(question))