"""Testes de segurança da exposição do link/OTP na resposta da API.

Garantem que:
- sem SMTP (dev): os códigos aparecem na resposta (único jeito de logar);
- com SMTP + SHOW_DEV_LOGIN_CODES: aparecem (atalho de dev);
- com SMTP + flag desligada: NÃO aparecem;
- em PRODUÇÃO: NUNCA aparecem, mesmo com a flag ligada (falha fechada).

A decisão fica em settings.expose_login_codes (server-side). Nada no request do
cliente pode alterá-la.
"""
import app.api.routes.auth as auth_routes


def _post_magic(client):
    return client.post("/auth/magic-link", json={"email": "x@test.com"}).json()


def test_sem_smtp_expoe_codigos(client, monkeypatch):
    # ambiente de teste: sem SMTP -> expõe
    monkeypatch.setattr(auth_routes.settings, "SMTP_USER", "")
    monkeypatch.setattr(auth_routes.settings, "SMTP_PASSWORD", "")
    monkeypatch.setattr(auth_routes.settings, "ENVIRONMENT", "development")
    body = _post_magic(client)
    assert body["dev_otp_code"]
    assert body["dev_magic_url"]


def test_com_smtp_e_flag_ligada_expoe(client, monkeypatch):
    monkeypatch.setattr(auth_routes.settings, "SMTP_HOST", "smtp-relay.brevo.com")
    monkeypatch.setattr(auth_routes.settings, "SMTP_USER", "u")
    monkeypatch.setattr(auth_routes.settings, "SMTP_PASSWORD", "p")
    monkeypatch.setattr(auth_routes.settings, "SHOW_DEV_LOGIN_CODES", True)
    monkeypatch.setattr(auth_routes.settings, "ENVIRONMENT", "development")
    # evita envio real de email
    monkeypatch.setattr(auth_routes, "send_login_email", lambda *a, **k: None)
    body = _post_magic(client)
    assert body["email_sent"] is True
    assert body["dev_otp_code"]  # atalho de dev


def test_com_smtp_e_flag_desligada_nao_expoe(client, monkeypatch):
    monkeypatch.setattr(auth_routes.settings, "SMTP_HOST", "smtp-relay.brevo.com")
    monkeypatch.setattr(auth_routes.settings, "SMTP_USER", "u")
    monkeypatch.setattr(auth_routes.settings, "SMTP_PASSWORD", "p")
    monkeypatch.setattr(auth_routes.settings, "SHOW_DEV_LOGIN_CODES", False)
    monkeypatch.setattr(auth_routes.settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(auth_routes, "send_login_email", lambda *a, **k: None)
    body = _post_magic(client)
    assert body["email_sent"] is True
    assert body["dev_otp_code"] is None
    assert body["dev_magic_url"] is None


def test_producao_nunca_expoe_mesmo_com_flag(client, monkeypatch):
    # PRODUÇÃO + SMTP + flag ligada => ainda assim NÃO expõe (falha fechada)
    monkeypatch.setattr(auth_routes.settings, "SMTP_HOST", "smtp-relay.brevo.com")
    monkeypatch.setattr(auth_routes.settings, "SMTP_USER", "u")
    monkeypatch.setattr(auth_routes.settings, "SMTP_PASSWORD", "p")
    monkeypatch.setattr(auth_routes.settings, "SHOW_DEV_LOGIN_CODES", True)
    monkeypatch.setattr(auth_routes.settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(auth_routes, "send_login_email", lambda *a, **k: None)
    body = _post_magic(client)
    assert body["email_sent"] is True
    assert body["dev_otp_code"] is None
    assert body["dev_magic_url"] is None


def test_request_nao_pode_forcar_exposicao(client, monkeypatch):
    """Mesmo passando campos extras no corpo, o cliente não ativa a exposição."""
    monkeypatch.setattr(auth_routes.settings, "SMTP_HOST", "smtp-relay.brevo.com")
    monkeypatch.setattr(auth_routes.settings, "SMTP_USER", "u")
    monkeypatch.setattr(auth_routes.settings, "SMTP_PASSWORD", "p")
    monkeypatch.setattr(auth_routes.settings, "SHOW_DEV_LOGIN_CODES", False)
    monkeypatch.setattr(auth_routes.settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(auth_routes, "send_login_email", lambda *a, **k: None)
    r = client.post(
        "/auth/magic-link",
        json={
            "email": "x@test.com",
            "show_dev_login_codes": True,
            "expose_codes": True,
            "debug": True,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["dev_otp_code"] is None
    assert body["dev_magic_url"] is None


def test_falha_no_envio_nao_derruba_request(client, monkeypatch):
    """Se o envio de email falhar, o endpoint responde 200 (email_sent=False),
    não 500. O pedido de login foi criado e pode ser reusado."""
    monkeypatch.setattr(auth_routes.settings, "SMTP_HOST", "smtp-relay.brevo.com")
    monkeypatch.setattr(auth_routes.settings, "SMTP_USER", "u")
    monkeypatch.setattr(auth_routes.settings, "SMTP_PASSWORD", "p")
    monkeypatch.setattr(auth_routes.settings, "ENVIRONMENT", "production")

    def boom(*a, **k):
        raise TimeoutError("smtp blocked")

    monkeypatch.setattr(auth_routes, "send_login_email", boom)

    r = client.post("/auth/magic-link", json={"email": "x@test.com"})
    assert r.status_code == 200
    body = r.json()
    assert body["email_sent"] is False
    assert body["selector"]
    # em produção, mesmo com falha, não expõe os códigos
    assert body["dev_otp_code"] is None


def test_brevo_api_enabled_quando_ha_api_key(monkeypatch):
    """email_enabled cobre o canal Brevo API mesmo sem SMTP_USER/PASSWORD."""
    from app.core.config import settings as cfg

    monkeypatch.setattr(cfg, "SMTP_USER", "")
    monkeypatch.setattr(cfg, "SMTP_PASSWORD", "")
    monkeypatch.setattr(cfg, "BREVO_API_KEY", "xkeysib-abc")
    monkeypatch.setattr(cfg, "SMTP_FROM", "remetente@dominio.com")
    assert cfg.brevo_api_enabled is True
    assert cfg.email_enabled is True
    assert cfg.smtp_enabled is False
