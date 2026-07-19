from pathlib import Path


def test_automation_expone_encolado_acotado_y_protegido_por_el_router_global():
    source = Path("mh_core/routes/automation_routes.py").read_text(encoding="utf-8")
    app = Path("mh_core/app.py").read_text(encoding="utf-8")
    assert '@router.post("/enqueue"' in source
    assert '"automation.run_once"' in source
    assert "payload" not in source.split("class AutomationJobRequest", 1)[1].split("@router.get", 1)[0]
    assert "app.include_router(automation_router, dependencies=_mindhigh_execute)" in app
