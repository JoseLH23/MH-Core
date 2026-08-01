from pathlib import Path


def test_render_inicia_runtime_minimo_gratuito_con_un_worker():
    blueprint = Path("render.yaml").read_text(encoding="utf-8")

    assert "apps.mindhigh.marketing_app:app" in blueprint
    assert "mh_core.marketing_app:app" not in blueprint
    assert "--workers 1" in blueprint
    assert "plan: free" in blueprint
    assert "healthCheckPath: /health/ready" in blueprint
    assert "autoDeployTrigger: checksPass" in blueprint
    assert "MH_ENVIRONMENT" in blueprint
    assert "value: production" in blueprint
    assert "MH_CORE_ALLOW_LEGACY_API_KEY" in blueprint
    assert 'value: "false"' in blueprint
    assert "MH_KNOWLEDGE_BUNDLE_PATH" in blueprint
    assert "/etc/secrets/approved-bundle.json" in blueprint
    assert "MH_CORE_EJIXHOLE_KEY" in blueprint
    assert "sync: false" in blueprint


def test_runtime_marketing_no_instala_dependencias_pesadas():
    requirements = Path("requirements-marketing.txt").read_text(encoding="utf-8")

    assert "fastapi==" in requirements
    assert "uvicorn[standard]==" in requirements
    assert "pydantic==" in requirements
    assert "python-dotenv==" in requirements
    assert "google-genai" not in requirements
    assert "pyttsx3" not in requirements
    assert "SQLAlchemy" not in requirements
