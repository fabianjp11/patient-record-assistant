import json
import re
from pathlib import Path
from functools import lru_cache

DATA_DIR = Path(__file__).parent / "data"


@lru_cache
def load_bundles() -> dict[str, list[dict]]:
    """Read every JSON file in data/ and return {patient_id: [resources...]}."""
    bundles = {}
    for path in sorted(DATA_DIR.glob("*.json")):
        with path.open(encoding="utf-8") as file:
            bundle = json.load(file)

        entries = bundle.get("entry", [])
        resources = [entry["resource"] for entry in entries]
        patient = next(
            (resource for resource in resources if resource.get("resourceType") == "Patient"),
            None,
        )
        if (
            not isinstance(patient, dict)
            or not isinstance(patient.get("id"), str)
            or not patient["id"]
        ):
            raise ValueError(f"{path} does not contain a patient with an id")

        patient_id = patient["id"]
        if patient_id in bundles:
            raise ValueError(f"Duplicate patient id {patient_id!r} in {path}")
        bundles[patient_id] = resources

    return bundles


def list_patients() -> list[dict]:
    """[{"id": ..., "name": "Cleo Paucek", "gender": ..., "birth_date": ...}, ...]"""
    patients = []
    for patient_id, resources in load_bundles().items():
        patient = next(
            resource for resource in resources if resource.get("resourceType") == "Patient"
        )
        raw_names = patient.get("name", [])
        names = (
            [item for item in raw_names if isinstance(item, dict)]
            if isinstance(raw_names, list)
            else []
        )
        name = next((item for item in names if item.get("use") == "official"), None)
        if name is None:
            name = names[0] if names else {}

        given_names = name.get("given", [])
        if not isinstance(given_names, list):
            given_names = []
        family_name = name.get("family", "")
        name_parts = [
            re.sub(r"\d+$", "", part)
            for part in [*given_names[:1], family_name]
            if isinstance(part, str) and part
        ]
        patients.append(
            {
                "id": patient_id,
                "name": " ".join(name_parts),
                "gender": patient.get("gender"),
                "birth_date": patient.get("birthDate"),
            }
        )

    return patients


def _condition_value(condition: dict, prefix: str):
    value = condition.get(f"{prefix}DateTime")
    if value is not None:
        return value

    period = condition.get(f"{prefix}Period", {})
    if period:
        boundary = "start" if prefix == "onset" else "end"
        return period.get(boundary) or period.get("start") or period.get("end")

    age = condition.get(f"{prefix}Age", {})
    if age:
        return age.get("value")
    return condition.get(f"{prefix}String")


def get_conditions(patient_id: str, active_only: bool = False) -> list[dict]:
    """[{"condition": ..., "status": ..., "onset": ..., "resolved": ...}, ...]
    Raise KeyError (or ValueError) if the patient_id doesn't exist."""
    bundles = load_bundles()
    if patient_id not in bundles:
        raise KeyError(f"Unknown patient id: {patient_id}")

    conditions = []
    for resource in bundles[patient_id]:
        if resource.get("resourceType") != "Condition":
            continue

        clinical_status = resource.get("clinicalStatus", {})
        codings = clinical_status.get("coding", [])
        status = codings[0].get("code") if codings else clinical_status.get("text")
        if active_only and status != "active":
            continue

        code = resource.get("code", {})
        code_codings = code.get("coding", [])
        condition_name = code.get("text")
        if condition_name is None and code_codings:
            condition_name = code_codings[0].get("display")

        conditions.append(
            {
                "condition": condition_name,
                "status": status,
                "onset": _condition_value(resource, "onset"),
                "resolved": _condition_value(resource, "abatement"),
            }
        )

    return conditions

if __name__ == "__main__":
    print(get_conditions(list_patients()[0]["id"], True))