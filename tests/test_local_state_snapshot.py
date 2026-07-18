from pathlib import Path

import pytest

from scripts.local_state_snapshot import create_snapshot, restore_snapshot, verify_snapshot


def test_snapshot_roundtrip_preserva_archivos(tmp_path: Path) -> None:
    root = tmp_path / "project"
    source = root / "mh_core" / "database"
    source.mkdir(parents=True)
    (source / "memory.json").write_text('{"items": [1, 2]}\n', encoding="utf-8")
    nested = source / "learning"
    nested.mkdir()
    (nested / "history.json").write_text('{"ok": true}\n', encoding="utf-8")
    (root / ".env").write_text("SECRET=no-debe-salir\n", encoding="utf-8")

    snapshot = tmp_path / "state.tar.gz"
    manifest = create_snapshot(root, [Path("mh_core/database"), Path(".env")], snapshot)

    assert snapshot.is_file()
    assert len(manifest["files"]) == 2
    assert all(item["path"] != ".env" for item in manifest["files"])
    assert verify_snapshot(snapshot) == manifest

    restored = tmp_path / "restored"
    restore_snapshot(snapshot, restored)

    assert (restored / "mh_core/database/memory.json").read_text(encoding="utf-8") == '{"items": [1, 2]}\n'
    assert (restored / "mh_core/database/learning/history.json").read_text(encoding="utf-8") == '{"ok": true}\n'
    assert not (restored / ".env").exists()


def test_restore_rechaza_destino_no_vacio(tmp_path: Path) -> None:
    root = tmp_path / "project"
    source = root / "data"
    source.mkdir(parents=True)
    (source / "state.json").write_text("{}", encoding="utf-8")
    snapshot = tmp_path / "state.tar.gz"
    create_snapshot(root, [Path("data")], snapshot)

    target = tmp_path / "target"
    target.mkdir()
    (target / "existing.txt").write_text("no reemplazar", encoding="utf-8")

    with pytest.raises(ValueError, match="no está vacío"):
        restore_snapshot(snapshot, target)
