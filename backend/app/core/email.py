"""Envio de email do login passwordless (magic link + código OTP).

Usa SMTP (defaults preparados para o Brevo). Se o SMTP não estiver configurado
(SMTP_HOST/USER/PASSWORD), opera em "modo dev": não envia nada e o link + código
são devolvidos na resposta da API, para testes locais (inclusive cross-device).

O template é inspirado no email do projeto "Planilha Versionada": oferece as duas
opções — digitar o código de 6 dígitos OU clicar no botão para aprovar o login.
"""
from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

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
    """Envia o email com magic link + código OTP. No modo dev não faz nada."""
    if not settings.smtp_enabled:
        return

    message = EmailMessage()
    message["Subject"] = f"Seu acesso ao {settings.APP_NAME}"
    from_addr = settings.SMTP_FROM or settings.SMTP_USER
    message["From"] = formataddr((settings.SMTP_FROM_NAME, from_addr))
    message["To"] = to_email
    message.set_content(_build_text(magic_url, otp_code))
    message.add_alternative(_build_html(magic_url, otp_code), subtype="html")

    _send(message)


def send_simple_email(to_email: str, subject: str, html: str, text: str) -> None:
    """Envia um email genérico (HTML + texto). Usado pelos alertas de projeto.

    No modo dev (sem SMTP) é um no-op. Não trata exceções — quem chama decide.
    """
    if not settings.smtp_enabled:
        return

    message = EmailMessage()
    message["Subject"] = subject
    from_addr = settings.SMTP_FROM or settings.SMTP_USER
    message["From"] = formataddr((settings.SMTP_FROM_NAME, from_addr))
    message["To"] = to_email
    message.set_content(text)
    message.add_alternative(html, subtype="html")

    _send(message)


def _send(message: EmailMessage) -> None:
    """Entrega a mensagem via SMTP (com ou sem STARTTLS)."""
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
