import pytest

from apps.mindhigh.services.prompt_manager import PromptManager

BRAIN_REPORT_EJEMPLO = {
    "executive_summary": {"topic": "ia en medicina"},
    "reasoning": ["razón real"],
    "recommended_actions": ["acción real"],
}


def test_content_generation_registrada_por_defecto():
    manager = PromptManager()
    assert "content_generation" in manager.listar_plantillas()


def test_render_produce_el_mismo_prompt_real():
    manager = PromptManager()
    prompt = manager.render("content_generation", brain_report=BRAIN_REPORT_EJEMPLO, duration_target="medio", style="cercano")

    assert "ia en medicina" in prompt
    assert "3 a 5 minutos" in prompt
    assert "cercano" in prompt


def test_plantilla_no_registrada_da_error_claro():
    manager = PromptManager()
    with pytest.raises(ValueError, match="no registrada"):
        manager.render("no-existe")


def test_registrar_plantilla_nueva_sin_tocar_las_existentes():
    manager = PromptManager()
    manager.registrar("prueba", lambda **kw: "prompt de prueba")

    assert manager.render("prueba") == "prompt de prueba"
    assert "content_generation" in manager.listar_plantillas()
