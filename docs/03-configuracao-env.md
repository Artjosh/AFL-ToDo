# Configuração e variáveis de ambiente

[← Voltar ao índice](../README.md)

## Backend (`backend/.env`)
```env
APP_NAME=ToDo AFL
# development | production. Em production, segredos NUNCA são expostos na
# resposta da API e o startup exige SMTP + JWT_SECRET forte (falha fechada).
ENVIRONMENT=development
DATABASE_URL=sqlite:///./app.db

JWT_SECRET=change-me
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

MAGIC_LINK_EXPIRE_MINUTES=15
OTP_MAX_ATTEMPTS=5
BACKEND_PUBLIC_URL=http://localhost:8000

# Mostrar link/OTP na resposta da API em DEV, mesmo com SMTP ativo (atalho de
# teste). Sempre IGNORADO em produção (lá nunca expõe). Padrão: true.
SHOW_DEV_LOGIN_CODES=true

# SMTP via Brevo (sem SMTP_USER/PASSWORD = modo dev: link + código na tela)
SMTP_HOST=smtp-relay.brevo.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=no-reply@seudominio.com
SMTP_FROM_NAME=ToDo AFL
SMTP_USE_TLS=true

# Supabase (opcional — validação via JWKS + callback cross-device)
SUPABASE_URL=
SUPABASE_PUBLISHABLE_KEY=
SUPABASE_JWT_ISSUER=
SUPABASE_JWKS_URL=
SUPABASE_JWT_AUDIENCE=authenticated

FRONTEND_URL=http://localhost:3000

# Redis (opcional): tokens efêmeros, rate limit e realtime. Vazio = desativado.
REDIS_URL=
RATE_LIMIT_MAX=5
RATE_LIMIT_WINDOW_SECONDS=60
```

### Link/OTP na resposta e segurança (`SHOW_DEV_LOGIN_CODES` / `ENVIRONMENT`)
Para facilitar o desenvolvimento, a API pode devolver o link e o código OTP no
corpo da resposta (e o frontend os mostra na tela). Quem decide isso é o backend,
via `settings.expose_login_codes`, com **falha fechada**:

| ENVIRONMENT | SMTP | SHOW_DEV_LOGIN_CODES | Expõe códigos? |
|-------------|------|----------------------|----------------|
| development | off  | qualquer             | **sim** (único jeito de logar) |
| development | on   | true                 | **sim** (atalho de dev) |
| development | on   | false                | não |
| **production** | qualquer | **qualquer**     | **NUNCA** |

Pontos de segurança:
- A decisão é **100% server-side**. Não é uma variável `NEXT_PUBLIC_*`, **não vai
  para o bundle** do navegador, e **nenhum campo do request** (corpo/query/header)
  consegue ativá-la — impossível bypassar pelo cliente.
- Em **produção**, é sempre `False`, independentemente da flag: o código só chega
  pelo email. Além disso, o startup **recusa subir** em produção sem SMTP ou com
  `JWT_SECRET` fraco.

### SMTP via Brevo
- `SMTP_USER` é o **Login SMTP** do Brevo (formato `xxxxxxx@smtp-brevo.com`),
  **não** o seu email.
- `SMTP_PASSWORD` é a **SMTP key value** (gerada em *SMTP & API → SMTP*).
- `SMTP_FROM` precisa ser um **remetente verificado** na sua conta Brevo
  (*Senders, Domains & Dedicated IPs*), senão o envio é rejeitado.
- Sem `SMTP_USER`/`SMTP_PASSWORD`, o backend roda em **modo dev** (link + código
  na tela/resposta).

## Frontend (`frontend/.env.local`)
```env
NEXT_PUBLIC_API_URL=http://localhost:8000

# Supabase (opcional)
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=
# anon key legada (fallback opcional)
NEXT_PUBLIC_SUPABASE_ANON_KEY=
```

> Os arquivos `.env` / `.env.local` reais **não devem ser comitados** (já estão
> no `.gitignore`).
