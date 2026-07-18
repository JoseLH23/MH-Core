from mh_core.database.memory_repository_factory import create_memory_repository
from mh_core.database.sql_memory_repository import SqlMemoryRepository
from mh_core.models.memory import Memory
from mh_core.persistence.database import create_engine_for_url


def repository_for(tmp_path):
    url = f"sqlite+pysqlite:///{(tmp_path / 'memory.sqlite3').as_posix()}"
    return SqlMemoryRepository(create_engine_for_url(url))


def memory(topic):
    return Memory(topic=topic, decision="PRIORIZAR", best_url=f"video-{topic}")


def test_sql_memory_preserva_contrato_y_evitar_duplicados(tmp_path):
    repo = repository_for(tmp_path)
    first = repo.guardar(memory("inteligencia-artificial"))
    duplicate = repo.guardar(memory("inteligencia-artificial"))
    repo.guardar(memory("turismo-aventura"))

    assert duplicate.id == first.id
    assert repo.count() == 2
    assert len(repo.listar()) == 2
    assert repo.buscar_por_tema("artificial")[0].id == first.id
    assert repo.recientes(1)[0].topic == "turismo-aventura"


def test_factory_conserva_json_sin_url_sql(tmp_path, monkeypatch):
    monkeypatch.delenv("MH_DATABASE_URL", raising=False)
    repository = create_memory_repository(tmp_path / "history.json")
    saved = repository.guardar(memory("local"))
    assert repository.listar()[0].id == saved.id


def test_factory_usa_sql_cuando_hay_url(tmp_path, monkeypatch):
    url = f"sqlite+pysqlite:///{(tmp_path / 'configured.sqlite3').as_posix()}"
    monkeypatch.setenv("MH_DATABASE_URL", url)
    repository = create_memory_repository(tmp_path / "unused.json")
    assert isinstance(repository, SqlMemoryRepository)
    repository.guardar(memory("sql"))
    assert len(repository.listar()) == 1
