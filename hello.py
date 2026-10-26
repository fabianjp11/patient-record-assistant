import anthropic

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY automatically

response = client.messages.create(
    model="claude-opus-5-5",
    max_tokens=1024,
    messages=[{"role": "user", "content": "In one sentence: what is FHIR in healthcare?"}],
)

for block in response.content:
    if block.type == "text":
        print(block.text)

print(response.usage)  # tokens used: get used to watching this