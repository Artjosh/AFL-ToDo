# Autenticação (passwordless: magic link + OTP)

[← Voltar ao índice](../README.md)

Não existe senha nem tela de cadastro. O fluxo é:

1. O usuário informa o **email** e clica em "Enviar link de acesso".
2. O backend (ou a Supabase) envia um email com **duas opções**: um **link de
   acesso** (magic link) e um **código OTP de 6 dígitos**.
3. O **primeiro acesso já cria a conta** automaticamente — não há "registrar-se".
4. O usuário pode então:
   - **Clicar o link em qualquer dispositivo** (ex.: pedir no desktop, clicar no
     celular). A aba de origem fica em "aguardando" e faz **polling** — ao
     detectar a confirmação, entra sozinha (multi-device).
   - **Digitar o código de 6 dígitos** na própria aba (mesmo dispositivo).

O fluxo combina magic link + OTP com polling cross-device: a aba que iniciou o
login consulta o status periodicamente e entra sozinha assim que a confirmação
acontece em qualquer dispositivo.

## Modo 1 — Backend Python (magic link próprio)

- `POST /auth/magic-link` cria um pedido de login, persiste em `login_tokens`
  (com `selector` público para polling e `magic_token`/`otp_code` secretos),
  envia o email via SMTP (Brevo) e devolve o `selector`.
- O link aponta para `GET /auth/confirm?token=...`. Ao ser aberto (em qualquer
  device), o backend aprova o login e cria o usuário se for o 1º acesso.
- `POST /auth/login-status?selector=...` é o **polling**: quando aprovado, o
  backend emite o **JWT de sessão** e devolve o usuário. O token é **uso único**.
- `POST /auth/verify-otp` valida o **código de 6 dígitos** (com limite de
  tentativas via `OTP_MAX_ATTEMPTS`) e emite a sessão na hora.

## Modo 2 — Python Backend + Supabase Auth

- O frontend chama `supabase.auth.signInWithOtp({ email, shouldCreateUser: true })`
  — a Supabase envia link + OTP.
- **Multi-device:** o frontend cria um pedido em `POST /auth/supabase/start` e usa
  o `selector` no `emailRedirectTo`, apontando para `GET /auth/supabase/callback`.
  O callback troca o `token_hash` por uma sessão Supabase (server-side), guarda no
  pedido e marca como aprovado. A aba de origem pega a sessão via
  `/auth/login-status`.
- **Mesmo device / OTP:** o usuário digita o código e o frontend usa
  `supabase.auth.verifyOtp`; em seguida chama `POST /auth/supabase/sync`.
- Em ambos, o backend **valida o token da Supabase por JWKS** (o projeto usa
  ES256), checa issuer/audience e **espelha o usuário** no SQLite via
  `supabase_user_id`.

A lógica que resolve o modo está em `app/api/deps.py::get_current_user`: tenta
primeiro o JWT de sessão local; se falhar e a Supabase estiver configurada, valida
como token Supabase e espelha o usuário.

## Onde a sessão é guardada (padrão BFF)

O **token de sessão não vive no browser**. O frontend Next atua como **BFF**
(Backend-for-Frontend): o token fica num **cookie `httpOnly`** gerenciado pelos
route handlers do Next, e o browser nunca o enxerga via JavaScript.

- **Modo local:** o fim do login (OTP ou polling) é feito por `/api/auth/login`
  **no servidor do Next**. Ele fala com o backend, recebe o `access_token` e grava
  o cookie — devolvendo ao browser **apenas o usuário**. O token jamais toca o JS.
- **Modo Supabase:** o `supabase-js` obtém o `access_token` no browser e o envia
  **uma única vez** a `/api/auth/session`, que valida contra o backend e o guarda
  no cookie httpOnly. A partir daí, o browser não usa mais o token.
- **Chamadas de dados:** vão para `/api/py/*` (same-origin); o servidor do Next lê
  o cookie e injeta `Authorization: Bearer` ao repassar para o FastAPI.
- **Restaurar sessão (F5):** o `AuthProvider` chama `GET /api/auth/session`, que
  lê o cookie e devolve o usuário. **Logout** chama `DELETE /api/auth/session`.
- **WebSocket:** como o WS não usa o cookie de forma prática, o browser pede um
  **ticket efêmero** a `/api/auth/ws-ticket` (JWT `type=ws`, ~60s) e o usa uma vez
  na URL de conexão.

Detalhes de segurança e a ressalva do modo Supabase em
[Segurança → Padrão BFF](./13-seguranca.md).

## Link e código na tela (modo dev)

Por padrão, em desenvolvimento o backend **mostra o link e o código OTP na própria
tela** (e na resposta da API), facilitando o login sem abrir o email — **mesmo com
o SMTP configurado**. Isso é controlado por `SHOW_DEV_LOGIN_CODES` (padrão `true`).

- Com **SMTP configurado**: o email é enviado normalmente **e** os códigos também
  aparecem na tela, sob um aviso "Atalho de desenvolvimento".
- Sem **SMTP** (`SMTP_USER`/`SMTP_PASSWORD` vazios): não há envio de email; o link
  e o código aparecem na tela (único jeito de logar).
- Em **produção** (`ENVIRONMENT=production`): os códigos **nunca** são expostos na
  resposta, **independentemente** de `SHOW_DEV_LOGIN_CODES` (falha fechada) — o
  acesso é só pelo email. A decisão é server-side e não pode ser ativada pelo
  cliente (não vai para o bundle; nenhum campo do request a altera).

Ver todas as variáveis em [Configuração e .env](./03-configuracao-env.md).

## Tour guiado (onboarding)

No primeiro acesso à tela de login, um **tour guiado** estilo stepper aparece
automaticamente: cards com "Passo X de Y", botões **Voltar/Próximo**, barra de
progresso e **spotlight** destacando cada elemento (seletor de modo, campo de
email, multi-device). Aparece **uma única vez**
(persistido em `localStorage`) e pode ser reaberto pelo botão **?** na navbar.

> Os toasts e o tour usam a lógica de "já mostrado / já clicado / anti-spam" de
> `lib/toast-state.ts`, persistida em `localStorage`.

## Testar em outro dispositivo

Para pedir o link num device e confirmar em outro (multi-device real na rede
local), veja [Acesso por outro dispositivo na rede](./08-acesso-rede-multidevice.md).
