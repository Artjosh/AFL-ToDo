"""Testes do fluxo de autenticação local (magic link + OTP + polling)."""


def _extract_token(dev_magic_url: str) -> str:
    return dev_magic_url.split("token=", 1)[1]


def test_magic_link_modo_dev_retorna_link_e_otp(client):
    r = client.post("/auth/magic-link", json={"email": "a@test.com"})
    assert r.status_code == 200
    body = r.json()
    assert body["selector"]
    assert body["email"] == "a@test.com"
    assert body["email_sent"] is False  # modo dev (sem SMTP)
    assert body["dev_magic_url"]
    assert body["dev_otp_code"] and len(body["dev_otp_code"]) == 6


def test_polling_pendente_antes_de_confirmar(client):
    sel = client.post("/auth/magic-link", json={"email": "a@test.com"}).json()["selector"]
    r = client.post("/auth/login-status", params={"selector": sel})
    assert r.status_code == 200
    assert r.json()["status"] == "pending"
    assert r.json()["authenticated"] is False


def test_fluxo_link_aprova_e_polling_retorna_sessao(client):
    body = client.post("/auth/magic-link", json={"email": "a@test.com"}).json()
    token = _extract_token(body["dev_magic_url"])

    assert client.get("/auth/confirm", params={"token": token}).status_code == 200

    r = client.post("/auth/login-status", params={"selector": body["selector"]})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "approved"
    assert data["authenticated"] is True
    assert data["provider"] == "local"
    assert data["access_token"]
    assert data["user"]["email"] == "a@test.com"


def test_selector_e_uso_unico(client):
    body = client.post("/auth/magic-link", json={"email": "a@test.com"}).json()
    client.get("/auth/confirm", params={"token": _extract_token(body["dev_magic_url"])})
    client.post("/auth/login-status", params={"selector": body["selector"]})
    # segundo polling com o mesmo selector deve falhar (consumido)
    r = client.post("/auth/login-status", params={"selector": body["selector"]})
    assert r.status_code == 404


def test_otp_correto_autentica(client):
    body = client.post("/auth/magic-link", json={"email": "otp@test.com"}).json()
    r = client.post(
        "/auth/verify-otp",
        json={"selector": body["selector"], "code": body["dev_otp_code"]},
    )
    assert r.status_code == 200
    assert r.json()["access_token"]


def test_otp_incorreto_rejeitado(client):
    body = client.post("/auth/magic-link", json={"email": "otp@test.com"}).json()
    r = client.post(
        "/auth/verify-otp",
        json={"selector": body["selector"], "code": "000000"},
    )
    assert r.status_code == 400


def test_otp_formato_invalido_422(client):
    body = client.post("/auth/magic-link", json={"email": "otp@test.com"}).json()
    r = client.post(
        "/auth/verify-otp",
        json={"selector": body["selector"], "code": "12"},  # < 6 dígitos
    )
    assert r.status_code == 422


def test_link_confirm_token_invalido(client):
    r = client.get("/auth/confirm", params={"token": "nao-existe"})
    assert r.status_code == 400  # página de erro


def test_email_invalido_422(client):
    r = client.post("/auth/magic-link", json={"email": "nao-eh-email"})
    assert r.status_code == 422


def test_primeiro_acesso_cria_usuario_login_recorrente_reusa(client, login_local):
    headers1, _ = login_local("recorrente@test.com")
    id1 = client.get("/auth/me", headers=headers1).json()["id"]

    headers2, _ = login_local("recorrente@test.com")
    id2 = client.get("/auth/me", headers=headers2).json()["id"]

    assert id1 == id2  # mesmo email => mesmo usuário


def test_me_sem_token_401(client):
    assert client.get("/auth/me").status_code == 401


def test_me_token_invalido_401(client):
    r = client.get("/auth/me", headers={"Authorization": "Bearer lixo"})
    assert r.status_code == 401
