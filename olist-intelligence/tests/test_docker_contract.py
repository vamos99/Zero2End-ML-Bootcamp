"""Static Docker startup contract checks."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_dockerfile_uses_runtime_dependencies_and_default_shell():
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "FROM python:3.12-slim-bookworm" in dockerfile
    assert "libgomp1" in dockerfile
    assert "pip install --no-cache-dir -r requirements.txt" in dockerfile
    assert 'CMD ["bash"]' in dockerfile


def test_docker_compose_services_require_runtime_configuration():
    compose = (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    for service in ("mlflow:", "api:", "dashboard:"):
        assert service in compose

    assert "DATABASE_URL=sqlite:////app/olist.db" in compose
    assert "API_KEY=${API_KEY:?Set API_KEY in .env before starting Docker services}" in compose
    assert "MLFLOW_TRACKING_URI=http://mlflow:5000" in compose
    assert "API_URL=http://api:8000" in compose
    assert "uvicorn src.app:app --host 0.0.0.0 --port 8000 --reload" in compose
    assert "streamlit run src/dashboard.py --server.port 8501 --server.address 0.0.0.0" in compose
