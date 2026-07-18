import json

from mh_core.models.memory import Memory
from scripts.migrate_memory import migrate


def test_migracion_conserva_origen_y_no_duplica(tmp_path, monkeypatch):
    source = tmp_path / "history.json"
    records = [
        Memory(topic="uno", decision="TEST", best_url="uno").model_dump(mode="json"),
        Memory(topic="dos", decision="TEST", best_url="dos").model_dump(mode="json"),
    ]
    source.write_text(json.dumps(records), encoding="utf-8")
    url = f"sqlite+pysqlite:///{(tmp_path / 'target.sqlite3').as_posix()}"
    monkeypatch.setenv("MH_DATABASE_URL", url)

    assert migrate(source, apply=False)["source"] == 2
    assert migrate(source, apply=True)["migrated"] == 2
    assert migrate(source, apply=True)["migrated"] == 0
    assert source.exists()
