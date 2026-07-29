"""Generate deterministic CycloneDX inventories for Python and Node lockfiles."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from importlib.resources import files
from typing import Any

import jsonschema
from renewableops.config import PROJECT_ROOT

OUTPUT_DIR = PROJECT_ROOT / "artifacts" / "security"


def _component(
    *,
    name: str,
    version: str,
    ecosystem: str,
    development: bool = False,
) -> dict[str, object]:
    namespace = "pypi" if ecosystem == "python" else "npm"
    return {
        "type": "library",
        "name": name,
        "version": version,
        "purl": f"pkg:{namespace}/{name}@{version}",
        "scope": "optional" if development else "required",
    }


def _read_python_components() -> list[dict[str, object]]:
    import tomllib

    payload = tomllib.loads((PROJECT_ROOT / "uv.lock").read_text(encoding="utf-8"))
    packages = payload.get("package", [])
    rows = []
    for package in packages:
        if not isinstance(package, dict) or "version" not in package:
            continue
        rows.append(
            _component(
                name=str(package["name"]),
                version=str(package["version"]),
                ecosystem="python",
            )
        )
    return sorted(rows, key=lambda row: (str(row["name"]), str(row["version"])))


def _read_node_components() -> list[dict[str, object]]:
    payload: object = json.loads((PROJECT_ROOT / "package-lock.json").read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("package-lock.json must contain an object")
    packages = payload.get("packages")
    if not isinstance(packages, dict):
        raise ValueError("package-lock.json does not contain packages")
    rows = []
    for path, item in packages.items():
        if not path or not isinstance(item, dict) or "version" not in item:
            continue
        name = item.get("name")
        if not isinstance(name, str):
            name = str(path).removeprefix("node_modules/")
        rows.append(
            _component(
                name=name,
                version=str(item["version"]),
                ecosystem="node",
                development=bool(item.get("dev", False)),
            )
        )
    return sorted(rows, key=lambda row: (str(row["name"]), str(row["version"])))


def _bom(ecosystem: str, components: list[dict[str, object]]) -> dict[str, Any]:
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": (
            f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, f'renewableops-ai:{ecosystem}:1.0.0')}"
        ),
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(UTC).replace(microsecond=0).isoformat(),
            "component": {
                "type": "application",
                "name": f"renewableops-ai-{ecosystem}",
                "version": "1.0.0",
            },
            "properties": [
                {
                    "name": "renewableops:source",
                    "value": "uv.lock" if ecosystem == "python" else "package-lock.json",
                },
                {"name": "renewableops:generator", "value": "scripts/generate_sbom.py"},
            ],
        },
        "components": components,
    }


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    outputs = {
        "python.cdx.json": _bom("python", _read_python_components()),
        "node.cdx.json": _bom("node", _read_node_components()),
    }
    for name, payload in outputs.items():
        schema_path = files("cyclonedx.schema._res").joinpath(
            "bom-1.6.SNAPSHOT.schema.json"
        )
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema).validate(payload)
        (OUTPUT_DIR / name).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    print(
        json.dumps(
            {
                "status": "generated",
                "files": {
                    name: len(payload["components"])
                    for name, payload in outputs.items()
                },
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
