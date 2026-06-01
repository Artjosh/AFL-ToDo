"""Testes do modo Supabase e do vínculo por email entre os modos.

A verificação de assinatura do token Supabase (que depende de rede/JWKS) é
substituída por um mock; o que testamos é a lógica de espelhamento/vínculo do
usuário e o acesso às tarefas com um token "Supabase".
"""
import pytest

import app.api.deps as deps


@pytest.fixture()
def fake_supabase(monkeypatch):
    """Faz get_current_user aceitar tokens 'supabase:<uid>:<email>' como válidos."""
    monkeypatch.setattr(deps.settings, "SUPABASE_JWKS_URL", "https://exemplo/jwks")

    def fake_verify(token: str):
        # token no formato "uid|email"
        uid, email = token.split("|", 1)
        return {"sub": uid, "email": email, "aud": "authenticated"}

    monkeypatch.setattr(deps, "verify_supabase_token", fake_verify)
    return fake_verify


def _sb_headers(uid: str, email: str) -> dict:
    return {"Authorization": f"Bearer {uid}|{email}"}


def test_token_supabase_cria_usuario_espelhado(client, fake_supabase):
    h = _sb_headers("uid-123", "novo@supabase.com")
    r = client.get("/auth/me", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == "novo@supabase.com"
    assert data["supabase_user_id"] == "uid-123"


def test_supabase_sync_retorna_usuario(client, fake_supabase):
    h = _sb_headers("uid-xyz", "sync@supabase.com")
    r = client.post("/auth/supabase/sync", headers=h)
    assert r.status_code == 200
    assert r.json()["user"]["email"] == "sync@supabase.com"


def test_crud_tarefas_com_token_supabase(client, fake_supabase):
    h = _sb_headers("uid-task", "task@supabase.com")
    tid = client.post("/tasks", headers=h, json={"titulo": "via supabase"}).json()["id"]
    assert client.get("/tasks", headers=h).json()[0]["id"] == tid


def test_mesmo_supabase_uid_reusa_usuario(client, fake_supabase):
    h = _sb_headers("uid-fixo", "fixo@supabase.com")
    id1 = client.get("/auth/me", headers=h).json()["id"]
    id2 = client.get("/auth/me", headers=h).json()["id"]
    assert id1 == id2


def test_vinculo_por_email_local_para_supabase(client, login_local, fake_supabase):
    """Cenário crítico: criou no modo local, depois loga via Supabase (mesmo email).
    Deve reusar o MESMO usuário e preservar as tarefas."""
    # 1) cria no modo local + 1 tarefa
    headers_local, email = login_local("mesma@pessoa.com")
    me_local = client.get("/auth/me", headers=headers_local).json()
    client.post("/tasks", headers=headers_local, json={"titulo": "tarefa local"})

    # 2) agora chega um login Supabase com o MESMO email
    h_sb = _sb_headers("uid-da-supabase", email)
    me_sb = client.get("/auth/me", headers=h_sb).json()

    # mesmo usuário, agora com supabase_user_id vinculado
    assert me_sb["id"] == me_local["id"]
    assert me_sb["supabase_user_id"] == "uid-da-supabase"

    # tarefa criada no modo local continua visível no modo supabase
    tasks = client.get("/tasks", headers=h_sb).json()
    assert len(tasks) == 1
    assert tasks[0]["titulo"] == "tarefa local"


def test_emails_diferentes_sao_contas_distintas(client, login_local, fake_supabase):
    headers_local, _ = login_local("joao@test.com")
    client.post("/tasks", headers=headers_local, json={"titulo": "do joao"})

    h_sb = _sb_headers("uid-outro", "joao+outro@test.com")
    me_sb = client.get("/auth/me", headers=h_sb).json()
    me_local = client.get("/auth/me", headers=headers_local).json()

    assert me_sb["id"] != me_local["id"]
    assert client.get("/tasks", headers=h_sb).json() == []
