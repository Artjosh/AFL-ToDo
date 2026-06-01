"""Testes unitários de módulos do core (security, email, supabase_auth, request_origin)."""
import pytest

from app.core import security, supabase_auth
from app.core.supabase_auth import SupabaseAuthError


# ---- security (JWT de sessão) ----

def test_jwt_roundtrip():
    token = security.create_access_token(subject=42)
    payload = security.decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "42"
    assert payload["type"] == "access"


def test_jwt_invalido_retorna_none():
    assert security.decode_access_token("token.qualquer.invalido") is None


def test_jwt_tipo_errado_retorna_none(monkeypatch):
    # token assinado mas com type != access
    import jwt
    from app.core.config import settings

    bad = jwt.encode({"sub": "1", "type": "refresh"}, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    assert security.decode_access_token(bad) is None


# ---- supabase_auth (validação de token) ----

def test_verify_supabase_desabilitado(monkeypatch):
    monkeypatch.setattr(supabase_auth.settings, "SUPABASE_JWKS_URL", "")
    with pytest.raises(SupabaseAuthError):
        supabase_auth.verify_supabase_token("qualquer")


def test_verify_supabase_token_malformado(monkeypatch):
    monkeypatch.setattr(supabase_auth.settings, "SUPABASE_JWKS_URL", "https://exemplo/jwks")
    with pytest.raises(SupabaseAuthError):
        supabase_auth.verify_supabase_token("nao-e-jwt")


def test_verify_supabase_rejeita_hs256(monkeypatch):
    """Sistema novo só aceita chaves assimétricas (ES256/RS256). HS256 é recusado."""
    import jwt

    monkeypatch.setattr(supabase_auth.settings, "SUPABASE_JWKS_URL", "https://exemplo/jwks")
    monkeypatch.setattr(supabase_auth.settings, "SUPABASE_JWT_AUDIENCE", "")
    monkeypatch.setattr(supabase_auth.settings, "SUPABASE_JWT_ISSUER", "")
    token_hs256 = jwt.encode({"sub": "x"}, "qualquer-segredo", algorithm="HS256")
    with pytest.raises(SupabaseAuthError):
        supabase_auth.verify_supabase_token(token_hs256)


def test_verify_email_otp_hash_desabilitado(monkeypatch):
    monkeypatch.setattr(supabase_auth.settings, "SUPABASE_URL", "")
    monkeypatch.setattr(supabase_auth.settings, "SUPABASE_PUBLISHABLE_KEY", "")
    with pytest.raises(SupabaseAuthError):
        supabase_auth.verify_email_otp_hash("hash")


def test_verify_email_otp_hash_sucesso(monkeypatch):
    monkeypatch.setattr(supabase_auth.settings, "SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setattr(supabase_auth.settings, "SUPABASE_PUBLISHABLE_KEY", "sb_pk")

    class FakeResp:
        status_code = 200

        def json(self):
            return {"access_token": "AT", "refresh_token": "RT", "user": {"email": "a@b.com"}}

    monkeypatch.setattr(supabase_auth.httpx, "post", lambda *a, **k: FakeResp())
    data = supabase_auth.verify_email_otp_hash("hash-valido")
    assert data["access_token"] == "AT"
    assert data["user"]["email"] == "a@b.com"


def test_verify_email_otp_hash_falha_http(monkeypatch):
    monkeypatch.setattr(supabase_auth.settings, "SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setattr(supabase_auth.settings, "SUPABASE_PUBLISHABLE_KEY", "sb_pk")

    class FakeResp:
        status_code = 401

        def json(self):
            return {"error": "invalid"}

    monkeypatch.setattr(supabase_auth.httpx, "post", lambda *a, **k: FakeResp())
    with pytest.raises(SupabaseAuthError):
        supabase_auth.verify_email_otp_hash("hash-ruim")


# ---- email (modo dev vs envio) ----

def test_email_modo_dev_nao_envia(monkeypatch):
    from app.core import email

    monkeypatch.setattr(email.settings, "SMTP_HOST", "")
    monkeypatch.setattr(email.settings, "SMTP_USER", "")
    monkeypatch.setattr(email.settings, "SMTP_PASSWORD", "")
    called = {"sent": False}

    def fake_smtp(*a, **k):
        called["sent"] = True
        raise AssertionError("não deveria conectar no modo dev")

    monkeypatch.setattr(email.smtplib, "SMTP", fake_smtp)
    # não deve levantar nada nem tentar enviar
    email.send_login_email("a@b.com", "http://link", "123456")
    assert called["sent"] is False

