from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

MANIFEST = Path("release-manifest.json")
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate() -> dict:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    required = {"schema_version", "component", "version", "ecosystem_release"}
    if required - set(data):
        raise SystemExit("Manifiesto incompleto")
    if data["schema_version"] != 1 or data["component"] != "mh-core":
        raise SystemExit("Manifiesto incompatible")
    if not SEMVER.fullmatch(data["version"]):
        raise SystemExit("La versión no cumple SemVer")
    if os.getenv("GITHUB_REF_TYPE") == "tag" and os.getenv("GITHUB_REF_NAME") != f"v{data['version']}":
        raise SystemExit("La etiqueta no coincide con el manifiesto")
    return data


def write_evidence(data: dict, output: Path) -> None:
    files = [Path("release-manifest.json"), Path("requirements.txt")]
    payload = {
        "schema_version": 1,
        "component": data["component"],
        "version": data["version"],
        "ecosystem_release": data["ecosystem_release"],
        "commit": os.getenv("GITHUB_SHA", "local"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "files": {str(path): file_hash(path) for path in files if path.exists()},
        "contracts": [
            "mh-core.api.v1",
            "mh-core.observability.v1",
            "mh-core.jobs-durable.v1",
            "mh-core.ejixhole-analytics.v1"
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    data = validate()
    if args.evidence:
        write_evidence(data, args.evidence)
    print(f"release válido: {data['component']} v{data['version']}")


if __name__ == "__main__":
    main()
