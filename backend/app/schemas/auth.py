"""Schemas Pydantic para autenticação passwordless (magic link + OTP)."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class MagicLinkRequest(BaseModel):
    """Pedido de login: só o email (sem senha)."""

    email: EmailStr


class MagicLinkResponse(BaseModel):
    """Resposta ao solicitar o acesso.

    ``selector`` é usado pelo device de origem para fazer polling.
    No modo dev (sem SMTP), ``dev_magic_url`` e ``dev_otp_code`` trazem o link e
    o código direto para teste.
    """

    selector: str
    email: EmailStr
    email_sent: bool
    dev_magic_url: str | None = None
    dev_otp_code: str | None = None
    message: str


class OtpVerifyRequest(BaseModel):
    """Verificação do código OTP de 6 dígitos (modo local)."""

    selector: str
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    supabase_user_id: str | None = None
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class LoginStatusResponse(BaseModel):
    """Resposta do polling de status do login.

    No modo local, ``access_token`` é o JWT de sessão do backend.
    No modo Supabase cross-device, ``access_token`` é o token da Supabase (que o
    frontend usa como Bearer e o backend valida via JWKS).
    """

    status: str  # "pending" | "approved"
    authenticated: bool
    provider: str = "local"
    access_token: str | None = None
    refresh_token: str | None = None
    user: UserOut | None = None


class SupabaseSyncResponse(BaseModel):
    """Resposta da troca do token Supabase pela sessão local/usuário espelhado."""

    user: UserOut
