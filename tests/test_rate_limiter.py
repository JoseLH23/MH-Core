import time

from mh_core.core.rate_limiter import RateLimiter


def test_permite_hasta_el_maximo():
    limiter = RateLimiter(max_llamadas=3, ventana_segundos=60)

    assert limiter.permitido("k") is True
    assert limiter.permitido("k") is True
    assert limiter.permitido("k") is True


def test_bloquea_al_exceder_el_maximo():
    limiter = RateLimiter(max_llamadas=2, ventana_segundos=60)

    limiter.permitido("k")
    limiter.permitido("k")

    assert limiter.permitido("k") is False


def test_claves_distintas_no_se_afectan_entre_si():
    limiter = RateLimiter(max_llamadas=1, ventana_segundos=60)

    assert limiter.permitido("a") is True
    assert limiter.permitido("b") is True  # clave distinta, no comparte cupo


def test_ventana_deslizante_libera_cupo_con_el_tiempo():
    limiter = RateLimiter(max_llamadas=1, ventana_segundos=0.2)

    assert limiter.permitido("k") is True
    assert limiter.permitido("k") is False

    time.sleep(0.25)
    assert limiter.permitido("k") is True


def test_segundos_para_reintentar_es_razonable():
    limiter = RateLimiter(max_llamadas=1, ventana_segundos=10)
    limiter.permitido("k")
    limiter.permitido("k")  # bloqueado

    espera = limiter.segundos_para_reintentar("k")
    assert 0 < espera <= 10


# --- Integración real: el rate limit sí se aplica en un endpoint real -----


def test_rate_limit_real_en_endpoint_de_agentes():
    """Golpea /agents/research/run más veces que el límite configurado
    y confirma que la app real responde 429 — no solo que la clase
    RateLimiter funcione aislada."""
    from fastapi.testclient import TestClient

    from conftest import HEADERS_API_KEY
    from mh_core.app import app
    from mh_core.utils.rate_limit_dependency import limitador_generacion_ia

    limitador_generacion_ia._llamadas.clear()  # aislar de otros tests que ya hayan gastado el cupo
    client = TestClient(app)

    respuestas = [client.post("/agents/research/run", headers=HEADERS_API_KEY) for _ in range(11)]
    codigos = [r.status_code for r in respuestas]

    assert 429 in codigos, "debería haberse activado el límite tras 10 llamadas en la ventana"
