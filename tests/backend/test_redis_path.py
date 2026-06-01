"""Testes do caminho Redis (login tokens, rate limit) usando fakeredis.

Injetamos um fakeredis no client e exercitamos os mesmos fluxos de auth, agora
servidos pelo Redis em vez do banco — garantindo paridade de comportamento.
"""
import fakeredis
import pytest

import app.core.redis_client as redis_client
import app.core.rate_limit as rate_limit


@pytest.fixture()
def fake_redis(monkeypatch):
    """Faz get_redis() retornar um fakeredis e liga REDIS_URL/redis_enabled."""
    fake = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(redis_client.settings, "REDIS_URL", "redis://fake:6379/0")
    monkeypatch.setattr(redis_client, "get_redis", lambda: fake)
    # rate_limit e login store importam get_redis do módulo redis_client
    monkeypatch.setattr(rate_limit, "get_redis", lambda: fake)
    import app.services.login_tokens as lt
    monkeypatch.setattr(lt, "get_redis", lambda: fake)
    return fake


def _extract_token(dev_magic_url: str) -> str:
    return dev_magic_url.split("token=", 1)[1]


def test_fluxo_link_via_redis(client, fake_redis):
    body = client.post("/auth/magic-link", json={"email": "r@test.com"}).json()
    assert body["selector"]
    # o token está no Redis (fake), não na tabela
    assert fake_redis.get(f"login:sel:{body['selector']}") is not None

    token = _extract_token(body["dev_magic_url"])
    assert client.get("/auth/confirm", params={"token": token}).status_code == 200

    r = client.post("/auth/login-status", params={"selector": body["selector"]})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "approved" and data["access_token"]
    # consumido após aprovar
    assert fake_redis.get(f"login:sel:{body['selector']}") is None


def test_otp_via_redis(client, fake_redis):
    body = client.post("/auth/magic-link", json={"email": "otp-r@test.com"}).json()
    # código errado incrementa tentativa
    bad = client.post("/auth/verify-otp", json={"selector": body["selector"], "code": "000000"})
    assert bad.status_code == 400
    # código certo aprova
    ok = client.post("/auth/verify-otp", json={"selector": body["selector"], "code": body["dev_otp_code"]})
    assert ok.status_code == 200 and ok.json()["access_token"]


def test_selector_uso_unico_via_redis(client, fake_redis):
    body = client.post("/auth/magic-link", json={"email": "u@test.com"}).json()
    client.get("/auth/confirm", params={"token": _extract_token(body["dev_magic_url"])})
    client.post("/auth/login-status", params={"selector": body["selector"]})
    # segundo polling: consumido => 404
    r = client.post("/auth/login-status", params={"selector": body["selector"]})
    assert r.status_code == 404


def test_novo_pedido_invalida_anterior_via_redis(client, fake_redis):
    b1 = client.post("/auth/magic-link", json={"email": "x@test.com"}).json()
    b2 = client.post("/auth/magic-link", json={"email": "x@test.com"}).json()
    # o selector antigo foi invalidado
    assert fake_redis.get(f"login:sel:{b1['selector']}") is None
    assert fake_redis.get(f"login:sel:{b2['selector']}") is not None


def test_rate_limit_magic_link(client, fake_redis, monkeypatch):
    monkeypatch.setattr(rate_limit.settings, "RATE_LIMIT_MAX", 3)
    monkeypatch.setattr(rate_limit.settings, "RATE_LIMIT_WINDOW_SECONDS", 60)
    # 3 primeiras passam, a 4ª (mesmo email) é bloqueada
    ok = 0
    blocked = 0
    for _ in range(5):
        r = client.post("/auth/magic-link", json={"email": "flood@test.com"})
        if r.status_code == 200:
            ok += 1
        elif r.status_code == 429:
            blocked += 1
    assert ok == 3
    assert blocked == 2


def test_ttl_aplicado_no_token(client, fake_redis):
    body = client.post("/auth/magic-link", json={"email": "ttl@test.com"}).json()
    ttl = fake_redis.ttl(f"login:sel:{body['selector']}")
    assert ttl is not None and ttl > 0  # tem expiração automática
