"""Ponto de entrada da API FastAPI.

Configura CORS restrito ao frontend, registra as rotas e expõe um healthcheck.
As tabelas são criadas via Alembic (ver README). Como conveniência em ambiente
de desenvolvimento, também garantimos a criação das tabelas no startup caso o
banco ainda esteja vazio.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, projects, tasks, ws
from app.core.config import settings
from app.db.base_all import Base
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Conveniência para dev: cria as tabelas se ainda não existirem.
    # Em produção, use as migrations do Alembic (alembic upgrade head).
    Base.metadata.create_all(bind=engine)

    # Guarda de segurança: em produção, exigir configuração segura.
    if settings.is_production:
        if not settings.smtp_enabled:
            raise RuntimeError(
                "Produção sem SMTP: o login passwordless exige envio de email. "
                "Configure SMTP_* ou ajuste ENVIRONMENT."
            )
        if settings.JWT_SECRET in ("", "change-me"):
            raise RuntimeError(
                "Produção com JWT_SECRET inseguro. Defina um segredo forte "
                "(ex.: openssl rand -hex 32)."
            )

    # Captura o event loop principal para o realtime publicar a partir de rotas sync.
    import asyncio

    from app.services.realtime import set_main_loop

    set_main_loop(asyncio.get_running_loop())
    yield


app = FastAPI(
    title="To-Do API - Desafio AFL",
    description=(
        "API de tarefas com autenticação passwordless (magic link + JWT local) "
        "e modo integrado com Supabase Auth."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(ws.router)


@app.get("/", tags=["health"])
def root() -> dict[str, str]:
    return {"status": "ok", "service": "todo-api", "docs": "/docs"}


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "healthy"}
