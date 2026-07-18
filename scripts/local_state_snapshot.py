from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tarfile
import tempfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

MANIFEST_NAME = "_snapshot_manifest.json"
DEFAULT_SOURCES = (
    Path("mh_core/database"),
    Path("apps/mindhigh/database"),
    Path("data"),
    Path("logs"),
)
EXCLUDED_NAMES = {".env", ".env.local", ".env.production"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def should_include(path: Path) -> bool:
    if path.name in EXCLUDED_NAMES or path.suffix == ".pyc":
        return False
    return "__pycache__" not in path.parts and ".git" not in path.parts


def collect_files(root: Path, sources: list[Path]) -> list[tuple[Path, Path]]:
    collected: list[tuple[Path, Path]] = []
    root = root.resolve()
    for source in sources:
        absolute = (root / source).resolve() if not source.is_absolute() else source.resolve()
        if root not in absolute.parents and absolute != root:
            raise ValueError(f"La fuente está fuera del proyecto: {source}")
        if not absolute.exists():
            continue
        candidates = [absolute] if absolute.is_file() else sorted(absolute.rglob("*"))
        for candidate in candidates:
            if candidate.is_file() and should_include(candidate):
                collected.append((candidate, candidate.relative_to(root)))
    return sorted(set(collected), key=lambda item: item[1].as_posix())


def create_snapshot(root: Path, sources: list[Path], output: Path) -> dict[str, object]:
    files = collect_files(root, sources)
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "files": [
            {
                "path": relative.as_posix(),
                "size_bytes": absolute.stat().st_size,
                "sha256": sha256_file(absolute),
            }
            for absolute, relative in files
        ],
    }

    temporary = output.with_suffix(output.suffix + ".tmp")
    try:
        with tarfile.open(temporary, "w:gz") as archive:
            for absolute, relative in files:
                archive.add(absolute, arcname=relative.as_posix(), recursive=False)
            encoded = (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
            info = tarfile.TarInfo(MANIFEST_NAME)
            info.size = len(encoded)
            info.mtime = int(datetime.now(UTC).timestamp())
            with tempfile.SpooledTemporaryFile() as payload:
                payload.write(encoded)
                payload.seek(0)
                archive.addfile(info, payload)
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    return manifest


def safe_member_path(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"Ruta insegura en snapshot: {name}")
    return path


def read_manifest(archive: tarfile.TarFile) -> dict[str, object]:
    member = archive.getmember(MANIFEST_NAME)
    extracted = archive.extractfile(member)
    if extracted is None:
        raise ValueError("No se pudo leer el manifiesto")
    manifest = json.loads(extracted.read().decode("utf-8"))
    if manifest.get("schema_version") != 1 or not isinstance(manifest.get("files"), list):
        raise ValueError("Manifiesto de snapshot no soportado")
    return manifest


def verify_snapshot(snapshot: Path) -> dict[str, object]:
    with tarfile.open(snapshot, "r:gz") as archive:
        manifest = read_manifest(archive)
        members = {member.name: member for member in archive.getmembers() if member.isfile()}
        declared = manifest["files"]
        expected_names = {str(item["path"]) for item in declared}
        actual_names = set(members) - {MANIFEST_NAME}
        if expected_names != actual_names:
            raise ValueError("Los archivos del snapshot no coinciden con el manifiesto")

        for item in declared:
            name = str(item["path"])
            safe_member_path(name)
            extracted = archive.extractfile(members[name])
            if extracted is None:
                raise ValueError(f"No se pudo leer {name}")
            content = extracted.read()
            if len(content) != item["size_bytes"]:
                raise ValueError(f"Tamaño inválido en {name}")
            if hashlib.sha256(content).hexdigest() != item["sha256"]:
                raise ValueError(f"Checksum inválido en {name}")
        return manifest


def restore_snapshot(snapshot: Path, target: Path, overwrite: bool = False) -> dict[str, object]:
    manifest = verify_snapshot(snapshot)
    if target.exists() and any(target.iterdir()) and not overwrite:
        raise ValueError("El directorio destino no está vacío; usa --overwrite de forma explícita")
    target.mkdir(parents=True, exist_ok=True)

    with tarfile.open(snapshot, "r:gz") as archive:
        members = {member.name: member for member in archive.getmembers() if member.isfile()}
        for item in manifest["files"]:
            relative = safe_member_path(str(item["path"]))
            destination = target.joinpath(*relative.parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            source = archive.extractfile(members[relative.as_posix()])
            if source is None:
                raise ValueError(f"No se pudo extraer {relative}")
            with destination.open("wb") as output:
                shutil.copyfileobj(source, output)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Crear, verificar o restaurar snapshots del estado local de MH-Core.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create")
    create.add_argument("--root", type=Path, default=Path.cwd())
    create.add_argument("--source", action="append", type=Path, dest="sources")
    create.add_argument("--output", type=Path, required=True)

    verify = subparsers.add_parser("verify")
    verify.add_argument("--snapshot", type=Path, required=True)

    restore = subparsers.add_parser("restore")
    restore.add_argument("--snapshot", type=Path, required=True)
    restore.add_argument("--target", type=Path, required=True)
    restore.add_argument("--overwrite", action="store_true")

    args = parser.parse_args()
    try:
        if args.command == "create":
            manifest = create_snapshot(args.root, args.sources or list(DEFAULT_SOURCES), args.output)
            print(f"Snapshot creado: {args.output} ({len(manifest['files'])} archivos)")
        elif args.command == "verify":
            manifest = verify_snapshot(args.snapshot)
            print(f"Snapshot válido: {len(manifest['files'])} archivos")
        else:
            manifest = restore_snapshot(args.snapshot, args.target, args.overwrite)
            print(f"Snapshot restaurado en {args.target}: {len(manifest['files'])} archivos")
    except (OSError, ValueError, KeyError, json.JSONDecodeError, tarfile.TarError) as exc:
        print(f"Operación fallida: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
