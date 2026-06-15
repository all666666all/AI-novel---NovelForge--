"""Application wiring: the app imports cleanly and exposes its routes, and no
runtime module depends on removed code."""

from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def test_app_exposes_routes():
    from app.main import app

    paths = {route.path for route in app.routes}
    assert "/api/health" in paths
    assert any(p.startswith("/api/") for p in paths)


def test_no_dangling_deprecated_imports():
    offenders = []
    for path in BACKEND_ROOT.rglob("*.py"):
        if "tests" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "services._deprecated" in text or "services/_deprecated" in text:
            offenders.append(path.relative_to(BACKEND_ROOT))
    assert not offenders, f"references to removed services._deprecated: {offenders}"
