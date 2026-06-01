# Estrutura do projeto

[← Voltar ao índice](../README.md)

```
.
├── backend/
│   ├── app/
│   │   ├── main.py                 # App FastAPI + CORS + routers + lifespan
│   │   ├── core/
│   │   │   ├── config.py           # Settings (variáveis de ambiente)
│   │   │   ├── security.py         # JWT de sessão (sem senha)
│   │   │   ├── email.py            # Envio de email (magic link + OTP) via SMTP
│   │   │   ├── request_origin.py   # Descobre a URL pública do backend
│   │   │   └── supabase_auth.py    # Validação do JWT Supabase (JWKS) + verify token_hash
│   │   ├── db/
│   │   │   ├── session.py          # Engine/Session SQLAlchemy
│   │   │   ├── base.py             # Base declarativa
│   │   │   └── base_all.py         # Base + modelos (para Alembic/create_all)
│   │   ├── models/
│   │   │   ├── user.py             # Usuário (sem senha)
│   │   │   ├── task.py             # Tarefa
│   │   │   └── login_token.py      # Pedido de login (magic link + OTP + polling)
│   │   ├── schemas/                # Schemas Pydantic (auth, task)
│   │   └── api/
│   │       ├── deps.py             # get_current_user (resolve os 2 modos)
│   │       └── routes/
│   │           ├── auth.py         # magic-link, confirm, verify-otp, supabase/*, login-status, me
│   │           └── tasks.py        # CRUD de /tasks
│   ├── alembic/                    # Migrations
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── app/
│   │   ├── layout.tsx              # Providers (Toast, Auth) + Navbar
│   │   ├── page.tsx                # Redireciona login/dashboard
│   │   ├── login/page.tsx          # Login passwordless + tour guiado
│   │   ├── dashboard/page.tsx      # Board Kanban (rota protegida)
│   │   └── api/                    # BFF: route handlers server-side do Next
│   │       ├── auth/session/route.ts   # cookie httpOnly: set/get/clear sessão
│   │       ├── auth/login/route.ts     # fim do login local (OTP/polling) -> cookie
│   │       ├── auth/ws-ticket/route.ts # emite ticket efêmero para o WebSocket
│   │       └── py/[...path]/route.ts   # proxy /api/py/* -> FastAPI (injeta Bearer)
│   ├── components/
│   │   ├── auth-provider.tsx       # Contexto de auth (sem token no browser; 2 modos)
│   │   ├── auth-mode-selector.tsx  # Seletor de modo no topo
│   │   ├── auth-form.tsx           # Form passwordless + tela "aguardando" + OTP
│   │   ├── guided-tour.tsx         # Tour guiado (stepper com spotlight)
│   │   ├── navbar.tsx              # Navbar + botão "?" do tour
│   │   ├── board.tsx               # Board Kanban (colunas + drag-and-drop)
│   │   ├── board-card.tsx          # Card de tarefa
│   │   ├── task-detail-modal.tsx   # Detalhe/edição da tarefa + atribuídos
│   │   └── toast.tsx               # Sistema de toasts
│   ├── lib/
│   │   ├── api.ts                  # Cliente same-origin (chama o BFF, sem token)
│   │   ├── server-env.ts           # Config server-side do BFF (cookies, URL interna)
│   │   ├── realtime.ts             # WebSocket via ticket efêmero
│   │   ├── supabase.ts             # Browser client (publishable key)
│   │   ├── toast-state.ts          # Controle "mostrado/clicado/anti-spam"
│   │   └── types.ts
│   ├── middleware.ts               # Gating SSR (cookie) + refresh da sessão Supabase
│   ├── package.json
│   └── .env.example
│
├── docs/                           # Documentação detalhada (este diretório)
└── README.md                       # Índice / sumário
```
