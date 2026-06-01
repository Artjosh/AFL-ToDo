# Segurança

[← Voltar ao índice](../README.md)

- **CORS** liberado apenas para o `FRONTEND_URL` configurado (+ localhost em dev).
- **Sessão com expiração** (JWT, `ACCESS_TOKEN_EXPIRE_MINUTES`).
- **Magic link / OTP com expiração curta** (`MAGIC_LINK_EXPIRE_MINUTES`), **uso
  único** e **limite de tentativas** de OTP (`OTP_MAX_ATTEMPTS`).
- **Sem senha armazenada** — elimina toda uma classe de riscos.
- **Validação de ownership/membership** em todas as rotas — um usuário só acessa
  o que é dele ou foi compartilhado (respostas `404` para itens de outros, sem
  vazar existência).
- **Nunca confiar no `user_id` do frontend** — sempre derivado do token validado.
- **Token Supabase validado por JWKS** (assinatura ES256), com checagem de
  issuer/audience.
- **Variáveis de ambiente** para segredos; `.env` / `.env.local` no `.gitignore`.
- **Falha fechada em produção:** com `ENVIRONMENT=production`, a API **nunca**
  devolve o link/OTP no corpo da resposta (independe de `SHOW_DEV_LOGIN_CODES`), e
  o backend **recusa subir** sem SMTP ou com `JWT_SECRET` fraco. O atalho de
  mostrar o código na tela é exclusivo de desenvolvimento, decidido server-side
  (não vai para o bundle, nenhum campo do request o ativa).

## Padrão BFF (Backend-for-Frontend)

O frontend Next.js atua como um **BFF**: o token de sessão **nunca** é exposto ao
JavaScript do browser. Ele vive apenas num **cookie `httpOnly`** (`todo_session`),
gerenciado pelos route handlers do Next (`app/api/auth/*`).

- **Proxy de dados:** o browser chama rotas same-origin `/api/py/*`; o servidor
  do Next lê o cookie httpOnly e injeta `Authorization: Bearer` ao repassar para
  o FastAPI. O FastAPI continua sendo a **fonte de verdade** e revalida o token
  em toda requisição.
- **Fim do login no servidor:** no modo local, `/api/auth/login` recebe o
  OTP/polling, fala com o backend e grava o cookie — devolvendo ao browser
  **apenas o usuário**, nunca o token.
- **WebSocket por ticket:** como o WS não usa o cookie httpOnly de forma prática,
  o browser pede a `/api/auth/ws-ticket` um **ticket efêmero** (JWT `type=ws`,
  ~60s) e o usa uma única vez na URL de conexão. Mesmo se vazar, expira em
  segundos e só serve para abrir o WS.
- **Gating SSR:** o `middleware.ts` redireciona `/dashboard` → `/login` (e
  vice-versa) com base na presença do cookie, sem flash de conteúdo.

**Ganho:** mesmo com um XSS, não há token de sessão acessível via
`document`/`localStorage` para ser roubado.

**Ressalva (modo Supabase, mesmo device):** o `supabase-js` roda no browser e
manipula o access_token por um instante antes de ele ser enviado uma única vez a
`/api/auth/session` (que o guarda no cookie httpOnly). No **modo Backend Python**
(recomendado) o token de sessão jamais toca o JavaScript.
