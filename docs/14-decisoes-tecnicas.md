# Decisões técnicas

[← Voltar ao índice](../README.md)

- **Passwordless por design.** Não há senha nem hash; o login é por magic link +
  OTP e o primeiro acesso cria a conta. Segue o conceito do projeto `gaming-cloud`.
- **Polling cross-device.** O modo local persiste o pedido de login em
  `login_tokens` (`selector` público + `magic_token`/`otp_code` secretos). A aba
  de origem faz polling pelo `selector`; o link pode ser aberto em outro device.
  No modo Supabase, o link volta ao callback do backend, que troca o `token_hash`
  por sessão e marca o pedido como aprovado — a aba de origem busca via polling.
- **Backend como fonte de verdade das tarefas.** Mesmo no modo Supabase, as
  tarefas nunca são lidas/escritas direto pelo frontend; tudo passa pela API
  Python. O `user_id` jamais vem do frontend — é derivado do token em
  `get_current_user`.
- **Frontend como BFF (Backend-for-Frontend).** O servidor do Next fica entre o
  browser e o FastAPI: guarda o token de sessão num **cookie `httpOnly`** (fora do
  alcance do JavaScript) e expõe um proxy same-origin (`/api/py/*`) que injeta o
  `Authorization: Bearer` no servidor. O FastAPI continua sendo a fonte de verdade
  e revalida o token a cada chamada — o BFF é só uma camada de borda (auth + proxy
  + gating de rota), **sem regra de negócio nem banco**. O WebSocket usa um
  **ticket efêmero** (`/auth/ws-ticket`) já que não usa o cookie. Detalhes e a
  ressalva do modo Supabase em [Segurança → Padrão BFF](./13-seguranca.md).
  - **Escopo do que foi feito:** protege o token (cookie httpOnly), centraliza as
    chamadas no servidor do Next e faz **gating de rota no middleware**
    (`/dashboard`↔`/login` sem flash). **Não** convertemos o dashboard para SSR de
    dados — ele segue client component buscando via proxy; isso poderia ser um
    próximo passo, mas não era necessário para proteger a sessão.
- **Supabase só para auth.** Validação do token por **JWKS** (chave pública), sem
  necessidade de secret key, sem tabelas e sem ORM do lado da Supabase.
- **Um único modelo `User`** para os dois modos (`supabase_user_id` nulo no modo
  local), facilitando o espelhamento.
- **Toasts + tour inspirados no `ats-example`:** estilo escuro com acento roxo e a
  lógica de "já mostrado / já clicado / anti-spam" (`lib/toast-state.ts`),
  persistida em `localStorage`.
- **SMTP opcional (Brevo):** em dev o link + código aparecem na tela; em produção,
  configure o SMTP.
- **Sem overengineering:** SQLite + SQLAlchemy + Alembic cobrem o desafio.

## Chaves/secrets da Supabase — o que o backend precisa (e o que NÃO precisa)

O projeto usa o **sistema novo de "JWT Signing Keys"** da Supabase, com chaves
**assimétricas (ES256 / ECC P-256)** — o JWKS do projeto expõe apenas `alg=ES256`.

> **"JWT Keys" e "JWKS" são a mesma coisa, vistas de dois lados.** Em *JWT Keys*
> (painel) você gerencia as chaves que assinam os tokens; o *JWKS*
> (`.../auth/v1/.well-known/jwks.json`) é o endpoint público que publica a **parte
> pública** dessas chaves. O backend baixa o JWKS e valida a assinatura com a
> chave pública.

Consequências:

- **`SUPABASE_PUBLISHABLE_KEY`** (`sb_publishable_...`): único valor da Supabase no
  backend. É **público** (também usado no frontend). Serve para o callback
  cross-device chamar `/auth/v1/verify`.
- **JWKS público**: a assinatura do token é validada com a **chave pública**
  baixada do `SUPABASE_JWKS_URL`. Não exige nenhum segredo.
- **HS256 / `SUPABASE_JWT_SECRET` foram removidos.** O "Legacy HS256 Shared Secret"
  do painel é a chave **anterior**, já migrada para as JWT Signing Keys. Como o
  projeto não emite tokens HS256, o backend **recusa** HS256 e não guarda nenhum
  segredo — a variável nem existe mais no `.env`.
- **`sb_secret_...` (secret key da Supabase): NÃO usar no backend.** Não é
  necessária — a validação é criptográfica via chave pública.

Resumo: o backend valida o login da Supabase **sem nenhum segredo** — apenas chave
pública (JWKS) + a publishable key.

## Observações sobre SQLite e deploy

- O SQLite é um arquivo (`backend/app.db`). Ótimo para dev e para o escopo do
  desafio, mas **filesystems efêmeros perdem o arquivo em redeploys**.
- Para deploy com persistência:
  - **Railway** com volume persistente;
  - **Fly.io** com volume persistente;
  - **Render** apenas com *persistent disk*.
- Migrar para Postgres é trivial: basta trocar a `DATABASE_URL`.
- Em produção, defina um `JWT_SECRET` forte, configure SMTP, ajuste `FRONTEND_URL`
  e `BACKEND_PUBLIC_URL`, e adicione as Redirect URLs na Supabase.

> Link de deploy: _(adicionar aqui caso seja publicado)._
