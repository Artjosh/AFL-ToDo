"""Configuração central da aplicação.

Carrega variáveis de ambiente usando pydantic-settings. Todas as configurações
sensíveis (segredos, URLs, SMTP) vêm de variáveis de ambiente / arquivo .env e
nunca devem ser comitadas.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "ToDo AFL"

    # Ambiente de execução. Em "production", segredos NUNCA são expostos na
    # resposta da API (falha fechada), independentemente de outras flags.
    ENVIRONMENT: str = "development"

    # Banco de dados
    DATABASE_URL: str = "sqlite:///./app.db"

    # JWT de sessão (emitido pelo backend após confirmar link/OTP no modo local)
    JWT_SECRET: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 dia

    # Magic link / OTP (passwordless do modo local)
    MAGIC_LINK_EXPIRE_MINUTES: int = 15
    OTP_MAX_ATTEMPTS: int = 5
    # URL pública do backend, usada para montar o link do email.
    # Se vazio, é derivada do request.
    BACKEND_PUBLIC_URL: str = ""

    # --- SMTP (envio de email do magic link no modo local) ---
    # Defaults preparados para o Brevo (https://www.brevo.com).
    # Preencha SMTP_USER (login SMTP do Brevo) e SMTP_PASSWORD (a chave SMTP).
    # Se SMTP_HOST OU as credenciais estiverem vazias, o backend opera em "modo
    # dev": não envia email e devolve link + código OTP na resposta da API.
    SMTP_HOST: str = "smtp-relay.brevo.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_FROM_NAME: str = "ToDo AFL"
    SMTP_USE_TLS: bool = True

    # --- Supabase (modo "Python Backend + Supabase Auth") ---
    # Usa chaves assimétricas (ES256/RS256) validadas pelo JWKS público do projeto.
    SUPABASE_URL: str = ""
    # Chave pública (publishable/anon) — usada pelo backend para validar OTP via
    # endpoint /auth/v1/verify (fluxo cross-device por link).
    SUPABASE_PUBLISHABLE_KEY: str = ""
    SUPABASE_JWT_ISSUER: str = ""
    SUPABASE_JWKS_URL: str = ""
    SUPABASE_JWT_AUDIENCE: str = "authenticated"

    # CORS / Frontend
    FRONTEND_URL: str = "http://localhost:3000"

    # --- Redis (opcional) ---
    # Quando definido, é usado para: tokens de login efêmeros (com TTL),
    # rate limiting e realtime (Pub/Sub). Se vazio, o backend faz fallback para
    # o banco (login tokens) e desativa rate limit/realtime — tudo continua
    # funcionando, ideal para dev/testes.
    REDIS_URL: str = ""

    # Rate limit (aplicado quando há Redis): nº de solicitações por janela.
    RATE_LIMIT_MAX: int = 5
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    # Em desenvolvimento, mostrar o link/OTP na própria tela (resposta da API)
    # MESMO com SMTP configurado. Facilita testar o login sem abrir o email.
    # IGNORADO em produção (ver `expose_login_codes`): nunca expõe lá.
    SHOW_DEV_LOGIN_CODES: bool = True

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.strip().lower() in ("production", "prod")

    @property
    def expose_login_codes(self) -> bool:
        """Decide se a API pode devolver link/OTP no corpo da resposta.

        Regra de segurança (falha fechada):
        - Em PRODUÇÃO: NUNCA expõe, independentemente de qualquer flag. O acesso
          é só pelo email enviado por SMTP.
        - Fora de produção: expõe se SHOW_DEV_LOGIN_CODES estiver ligada OU se não
          houver SMTP (modo dev puro, onde a tela é o único jeito de logar).
        """
        if self.is_production:
            return False
        return self.SHOW_DEV_LOGIN_CODES or not self.smtp_enabled

    @property
    def supabase_enabled(self) -> bool:
        """Indica se o modo Supabase está configurado (validação via JWKS)."""
        return bool(self.SUPABASE_JWKS_URL)

    @property
    def redis_enabled(self) -> bool:
        """Indica se há Redis configurado (tokens efêmeros, rate limit, realtime)."""
        return bool(self.REDIS_URL)

    @property
    def supabase_callback_enabled(self) -> bool:
        """Indica se o backend pode fazer o callback cross-device da Supabase."""
        return bool(self.SUPABASE_URL and self.SUPABASE_PUBLISHABLE_KEY)

    @property
    def smtp_enabled(self) -> bool:
        """Indica se há SMTP configurado para envio real de email."""
        return bool(self.SMTP_HOST and self.SMTP_USER and self.SMTP_PASSWORD)

    @property
    def cors_origins(self) -> list[str]:
        origins = {self.FRONTEND_URL.rstrip("/")}
        origins.add("http://localhost:3000")
        origins.add("http://127.0.0.1:3000")
        return [o for o in origins if o]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
