# Visão geral

[← Voltar ao índice](../README.md)

Aplicação completa de **lista de tarefas (to-do)** com **autenticação passwordless
(magic link + OTP)**, **backend em Python (FastAPI)** como fonte de verdade das
tarefas e **frontend em Next.js (TypeScript + TailwindCSS)**.

Cada usuário acessa **apenas as próprias tarefas**, e o backend valida o token em
toda requisição — o frontend nunca acessa tarefas sem passar pela validação do
backend.

## O que o sistema faz

O usuário **entra com o email** (sem senha), recebe um **link de acesso** e um
**código de 6 dígitos**, e então **gerencia tarefas** (criar, listar, editar,
alterar status e excluir). A interface dá feedback por **toasts** e tem um
**tour guiado** de onboarding no primeiro acesso.

Cada tarefa tem os campos: `id`, `titulo`, `descricao`, `status`, `data_criacao`
e `updated_at`.

## Os dois modos de autenticação

No **topo do site** há um seletor de modo de autenticação/backend:

1. **Backend Python** — o próprio FastAPI gera o magic link + OTP, controla o
   login e emite a sessão (JWT). Tudo passwordless.
2. **Python Backend + Supabase Auth** — o magic link/OTP é enviado pela
   **Supabase**; ao confirmar, o backend Python valida o token da Supabase (via
   JWKS) e espelha o usuário no SQLite.

> Em ambos os modos, **as tarefas vivem no backend Python** (fonte de verdade).
> A Supabase é usada **somente para autenticação**.

Detalhes do fluxo em [Autenticação](./09-autenticacao.md).

## Tecnologias usadas

**Backend**
- [FastAPI](https://fastapi.tiangolo.com/) — framework web
- [SQLAlchemy 2.0](https://www.sqlalchemy.org/) — ORM
- [Alembic](https://alembic.sqlalchemy.org/) — migrations
- [Pydantic v2](https://docs.pydantic.dev/) — validação
- [PyJWT](https://pyjwt.readthedocs.io/) — JWT (sessão local HS256 + validação Supabase ES256/RS256 via JWKS)
- **SQLite** — persistência
- [Uvicorn](https://www.uvicorn.org/) — servidor ASGI
- `smtplib` (stdlib) — envio de email via SMTP (Brevo)

**Frontend**
- [Next.js 15](https://nextjs.org/) (App Router) + React 19
- **TypeScript**
- **TailwindCSS**
- [@supabase/ssr](https://supabase.com/docs) — auth opcional via Supabase
