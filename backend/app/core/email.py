"""Envio de email do login passwordless (magic link + código OTP) e alertas.

Dois canais de envio, escolhidos automaticamente:

1. **API HTTP do Brevo** (porta 443) — usada quando `BREVO_API_KEY` está definida.
   Funciona em hospedagens que bloqueiam SMTP de saída (ex.: Railway).
2. **SMTP** (Brevo) — usado quando há `SMTP_USER`/`SMTP_PASSWORD` e não há API key.
   Ideal para rodar local.

Sem nenhum canal configurado, o backend opera em "modo dev": não envia email e o
link + código são devolvidos na resposta da API (ver `expose_login_codes`).

O template oferece as duas vias: digitar o código de 6 dígitos OU clicar no botão.
"""

from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

import httpx

from app.core.config import settings


def _build_html(magic_url: str, otp_code: str) -> str:
    return f"""\
<div style="max-width:480px;margin:0 auto;font-family:Arial,Helvetica,sans-serif;">
  <h2 style="margin:0 0 16px;color:#0f172a;">Entrar no {settings.APP_NAME}</h2>
  <p style="margin:0 0 16px;color:#334155;font-size:15px;line-height:1.6;">
    Use o código abaixo para entrar:
  </p>
  <div style="margin:0 0 24px;padding:16px 20px;background:#0f172a;border-radius:12px;display:inline-block;">
    <span style="font-size:28px;letter-spacing:6px;font-weight:700;color:#ffffff;">{otp_code}</span>
  </div>
  <p style="margin:0 0 16px;color:#334155;font-size:15px;line-height:1.6;">
    Ou aprove o login clicando abaixo:
  </p>
  <p style="margin:0 0 24px;">
    <a href="{magic_url}"
       style="display:inline-block;padding:14px 22px;border-radius:12px;background:#6C5CE7;color:#ffffff;text-decoration:none;font-size:15px;font-weight:700;">
      Aprovar login
    </a>
  </p>
  <p style="margin:0 0 12px;color:#64748b;font-size:14px;line-height:1.6;">
    Se o botão não funcionar, copie este link:
  </p>
  <p style="margin:0 0 24px;font-size:13px;line-height:1.6;word-break:break-all;color:#475569;">
    {magic_url}
  </p>
  <p style="margin:0;color:#94a3b8;font-size:13px;line-height:1.6;">
    O link e o código expiram em {settings.MAGIC_LINK_EXPIRE_MINUTES} minutos.
    Se você não pediu esse acesso, ignore este email.
  </p>
</div>"""


def _build_text(magic_url: str, otp_code: str) -> str:
    return (
        f"Entrar no {settings.APP_NAME}\n\n"
        f"Seu código de acesso: {otp_code}\n\n"
        f"Ou aprove o login por este link:\n{magic_url}\n\n"
        f"O link e o código expiram em {settings.MAGIC_LINK_EXPIRE_MINUTES} minutos. "
        "Se você não pediu esse acesso, ignore este email."
    )


def send_login_email(to_email: str, magic_url: str, otp_code: str) -> None:
    """Envia o email com magic link + código OTP. No modo dev (sem canal) não faz nada."""
    if not settings.email_enabled:
        return
    _deliver(
        to_email,
        subject=f"Seu acesso ao {settings.APP_NAME}",
        html=_build_html(magic_url, otp_code),
        text=_build_text(magic_url, otp_code),
    )


def send_simple_email(to_email: str, subject: str, html: str, text: str) -> None:
    """Envia um email genérico (HTML + texto). Usado pelos alertas de projeto.

    No modo dev (sem canal) é um no-op. Não trata exceções — quem chama decide.
    """
    if not settings.email_enabled:
        return
    _deliver(to_email, subject=subject, html=html, text=text)


def _deliver(to_email: str, subject: str, html: str, text: str) -> None:
    """Escolhe o canal: API HTTP do Brevo (porta 443) ou SMTP."""
    if settings.brevo_api_enabled:
        _send_via_brevo_api(to_email, subject, html, text)
    else:
        _send_via_smtp(to_email, subject, html, text)


def _send_via_brevo_api(to_email: str, subject: str, html: str, text: str) -> None:
    """Envia pela API transacional do Brevo (HTTPS, não bloqueada em cloud)."""
    from_email = settings.SMTP_FROM or settings.SMTP_USER
    payload = {
        "sender": {"email": from_email, "name": settings.SMTP_FROM_NAME},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html,
        "textContent": text,
    }
    resp = httpx.post(
        "https://api.brevo.com/v3/smtp/email",
        json=payload,
        headers={
            "api-key": settings.BREVO_API_KEY,
            "content-type": "application/json",
            "accept": "application/json",
        },
        timeout=20,
    )
    resp.raise_for_status()


def _send_via_smtp(to_email: str, subject: str, html: str, text: str) -> None:
    """Entrega a mensagem via SMTP (com ou sem STARTTLS)."""
    message = EmailMessage()
    message["Subject"] = subject
    from_addr = settings.SMTP_FROM or settings.SMTP_USER
    message["From"] = formataddr((settings.SMTP_FROM_NAME, from_addr))
    message["To"] = to_email
    message.set_content(text)
    message.add_alternative(html, subtype="html")

    if settings.SMTP_USE_TLS:
        context = ssl.create_default_context()
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as server:
            server.starttls(context=context)
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(message)
    else:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as server:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(message)
