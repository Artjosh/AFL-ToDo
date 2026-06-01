"""Testes das rotas Supabase cross-device: /supabase/start e /supabase/callback."""
import app.api.routes.auth as auth_routes


def test_supabase_start_cria_pedido_para_polling(client):
    r = client.post("/auth/supabase/start", json={"email": "cross@device.com"})
    assert r.status_code == 200
    selector = r.json()["selector"]

    # polling deve responder pending com provider supabase
    p = client.post("/auth/login-status", params={"selector": selector})
    assert p.status_code == 200
    assert p.json()["status"] == "pending"
    assert p.json()["provider"] == "supabase"


def test_callback_aprova_e_polling_devolve_sessao_supabase(client, monkeypatch):
    # 1) cria o pedido (device de origem)
    selector = client.post(
        "/auth/supabase/start", json={"email": "cross@device.com"}
    ).json()["selector"]

    # 2) mocka a troca do token_hash por sessão (sem rede)
    def fake_verify_hash(token_hash, otp_type="email"):
        return {
            "access_token": "SUPA_AT",
            "refresh_token": "SUPA_RT",
            "user": {"email": "cross@device.com"},
        }

    monkeypatch.setattr(auth_routes, "verify_email_otp_hash", fake_verify_hash)

    # 3) device 2 abre o link (callback)
    r = client.get(
        "/auth/supabase/callback",
        params={"token_hash": "hash-qualquer", "selector": selector},
        follow_redirects=False,
    )
    assert r.status_code == 200  # página de sucesso

    # 4) device de origem faz polling e recebe a sessão Supabase
    p = client.post("/auth/login-status", params={"selector": selector})
    assert p.status_code == 200
    data = p.json()
    assert data["status"] == "approved"
    assert data["provider"] == "supabase"
    assert data["access_token"] == "SUPA_AT"
    assert data["refresh_token"] == "SUPA_RT"
    assert data["user"]["email"] == "cross@device.com"


def test_callback_token_hash_invalido_mostra_erro(client, monkeypatch):
    from app.core.supabase_auth import SupabaseAuthError

    def fake_fail(token_hash, otp_type="email"):
        raise SupabaseAuthError("invalido")

    monkeypatch.setattr(auth_routes, "verify_email_otp_hash", fake_fail)

    r = client.get(
        "/auth/supabase/callback",
        params={"token_hash": "ruim", "selector": "qualquer"},
        follow_redirects=False,
    )
    assert r.status_code == 400
