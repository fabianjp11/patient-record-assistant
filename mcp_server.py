from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
import fhir_store

server = MCPServer(
    "patient-records",
    instructions="Read-only access to synthetic FHIR patient records: list patients and look up their conditions.",
)

@server.tool()
def list_patients() -> list[dict]:
    """List all patients with id, name, gender and birth date.
        Use this first to find a patient's id from their name."""
    return fhir_store.list_patients()

@server.tool()
def get_conditions(patient_id: str, active_only: bool = False) -> list[dict]:
    """Returns the list of conditions for a patient: condition, status, onset and resolved. "
                        "Use this to find a patient's conditions by Id"""
    try:
        return fhir_store.get_conditions(patient_id, active_only)
    except KeyError as exc:
        raise ToolError(str(exc)) from exc


if __name__ == "__main__":
    server.run()      # stdio by default