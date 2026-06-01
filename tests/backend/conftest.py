"""Fixtures compartilhadas dos testes de backend.

Cada teste roda com um banco SQLite isolado em arquivo temporário, e um
TestClient do FastAPI com a dependência get_db sobrescrita para usar esse banco.
A validação do token Supabase é "mockável" por teste (monkeypatch).
"""
import os
import sys
from pathlib import Path

import pytest

# Garante que o pacote "app" (em backend/) seja importável.
BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

# Configura o ambiente ANTES de importar a app (modo dev: sem SMTP).
os.environ.setdefault("DATABASE_URL", "sqlite:///./_pytest_tmp.db")
os.environ["SMTP_USER"] = ""
os.environ["SMTP_PASSWORD"] = ""
os.environ["JWT_SECRET"] = "test-secret"
os.environ["FRONTEND_URL"] = "http://localhost:3000"

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db.base_all import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def db_engine(tmp_path):
    db_file = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    TestingSessionLocal = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_engine, monkeypatch):
    """TestClient com get_db apontando para o banco isolado do teste.

    Também rebinda app.db.session.SessionLocal para o engine de teste, de modo
    que código que usa SessionLocal() diretamente (ex.: o WebSocket de realtime)
    também acesse o mesmo banco isolado.
    """
    TestingSessionLocal = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    import app.db.session as db_session_module

    monkeypatch.setattr(db_session_module, "SessionLocal", TestingSessionLocal)
    # ws.py importa SessionLocal por referência — atualiza lá também.
    import app.api.routes.ws as ws_module

    monkeypatch.setattr(ws_module, "SessionLocal", TestingSessionLocal)

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _extract_magic_token(dev_magic_url: str) -> str:
    """Extrai o token da dev_magic_url (.../auth/confirm?token=XXX)."""
    return dev_magic_url.split("token=", 1)[1]


@pytest.fixture()
def login_local(client):
    """Helper: faz o fluxo completo de login local e devolve (headers, email)."""

    def _login(email: str = "user@test.com", use_otp: bool = False):
        r = client.post("/auth/magic-link", json={"email": email})
        assert r.status_code == 200, r.text
        body = r.json()
        selector = body["selector"]

        if use_otp:
            r = client.post(
                "/auth/verify-otp",
                json={"selector": selector, "code": body["dev_otp_code"]},
            )
            assert r.status_code == 200, r.text
            token = r.json()["access_token"]
        else:
            token = _extract_magic_token(body["dev_magic_url"])
            assert client.get("/auth/confirm", params={"token": token}).status_code == 200
            r = client.post("/auth/login-status", params={"selector": selector})
            assert r.status_code == 200, r.text
            token = r.json()["access_token"]

        return {"Authorization": f"Bearer {token}"}, email

    return _login
