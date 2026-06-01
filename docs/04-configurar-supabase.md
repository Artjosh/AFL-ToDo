# Configurar a Supabase (opcional)

[← Voltar ao índice](../README.md)

A Supabase é usada **só para auth** — não precisa de tabelas, ORM nem migrations
do lado da Supabase.

## 1. Chaves (aba Connect / API Keys)
Use a **Publishable key** nova (`sb_publishable_...`) em:
- `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` (frontend), e
- `SUPABASE_PUBLISHABLE_KEY` (backend, usada no callback cross-device para
  verificar o `token_hash`).

A `anon key` legada é aceita apenas como fallback.

## 2. Site URL e Redirect URLs
Em *Authentication → URL Configuration*:

**Site URL** (campo único, base do projeto) — em produção, o domínio do frontend:
```
https://afl-to-do.vercel.app/
```

**Redirect URLs** (allowlist) — o callback fica no **backend** (onde o
`token_hash` é trocado). Use **wildcard `/**`** no fim:
```
https://afl-todo-production.up.railway.app/**
```

> **O `/**` é obrigatório, não opcional.** O frontend monta o `emailRedirectTo`
> como `<backend>/auth/supabase/callback?selector=XXX`, ou seja, **com query
> string dinâmica** (`?selector=...`). A Supabase faz match da allowlist tratando
> `.` e `/` como separadores; uma entrada fixa como
> `.../auth/supabase/callback` **não casa** com a URL que tem `?selector=...`, e a
> Supabase descarta o `redirect_to` e cai no **Site URL** (você vê o link ir para
> a raiz do site, com a URL quebrada). O `https://<backend>/**` casa com o caminho
> + query e resolve isso. (Doc oficial:
> [Redirect URLs / wildcards](https://supabase.com/docs/guides/auth/redirect-urls).)

Para **desenvolvimento local / mesma rede**, adicione também as variantes com o
IP/porta locais (ex.: `http://192.168.100.163:8000/**` e
`http://localhost:8000/**`).

Site URL e Redirect URLs sempre apontam para os domínios **públicos** em produção
(Vercel para o front, Railway/Render/Fly para o back). Domínio público com HTTPS,
sem porta explícita.

## 3. Template de email (Magic Link) e código OTP
Em *Authentication → Email Templates → Magic Link*, cole o conteúdo abaixo. O
`{{ .Token }}` é o **código de 6 dígitos** e o botão aponta para o **callback do
backend** levando o `token_hash` (fluxo multi-device):

```html
<div style="max-width:480px;margin:0 auto;font-family:Arial,Helvetica,sans-serif;">
  <h2 style="margin:0 0 16px;color:#0f172a;">Entrar no ToDo AFL</h2>
  <p style="margin:0 0 16px;color:#334155;font-size:15px;line-height:1.6;">
    Use o código abaixo para entrar:
  </p>
  <div style="margin:0 0 24px;padding:16px 20px;background:#0f172a;border-radius:12px;display:inline-block;">
    <span style="font-size:28px;letter-spacing:6px;font-weight:700;color:#ffffff;">{{ .Token }}</span>
  </div>
  <p style="margin:0 0 16px;color:#334155;font-size:15px;line-height:1.6;">
    Ou aprove o login clicando abaixo:
  </p>
  <p style="margin:0 0 24px;">
    <a href="{{ .RedirectTo }}&token_hash={{ .TokenHash }}&type=email"
       style="display:inline-block;padding:14px 22px;border-radius:12px;background:#6C5CE7;color:#ffffff;text-decoration:none;font-size:15px;font-weight:700;">
      Aprovar login
    </a>
  </p>
  <p style="margin:0 0 12px;color:#64748b;font-size:14px;line-height:1.6;">
    Se o botão não funcionar, copie este link:
  </p>
  <p style="margin:0 0 24px;font-size:13px;line-height:1.6;word-break:break-all;color:#475569;">
    {{ .RedirectTo }}&token_hash={{ .TokenHash }}&type=email
  </p>
  <p style="margin:0;color:#94a3b8;font-size:13px;line-height:1.6;">
    Se você não pediu esse acesso, ignore este email.
  </p>
</div>
```

> Este é o **mesmo template do backend Python** (`app/core/email.py`), adaptado
> às variáveis da Supabase: o código vira `{{ .Token }}` e o link de aprovação
> usa `{{ .RedirectTo }}&token_hash={{ .TokenHash }}&type=email`.
>
> **Atenção ao separador `&` (não `?`).** Aqui o `{{ .RedirectTo }}` **já vem com
> query string** (`.../callback?selector=...`), então o `token_hash` precisa ser
> anexado com **`&`**. Se usar `?` (`{{ .RedirectTo }}?token_hash=...`), a URL fica
> com dois `?` e quebra. Isso é diferente do exemplo padrão da doc da Supabase,
> onde o `{{ .RedirectTo }}` é a raiz e o caminho é anexado com `/auth/confirm?...`.

## 4. SMTP custom (Authentication → Emails → SMTP Settings)
O SMTP nativo da Supabase tem limite muito baixo. Ative **Enable custom SMTP** e
use as mesmas credenciais do Brevo do backend:

| Campo | Valor |
|-------|-------|
| Sender email address | remetente **verificado** no Brevo (ex.: `swrdacc@gmail.com`) |
| Sender name | `ToDo AFL` |
| Host | `smtp-relay.brevo.com` |
| Port number | `587` |
| Username | o **Login SMTP** do Brevo (ex.: `8403fa002@smtp-brevo.com`) — não é o seu email |
| Password | a **SMTP key** do Brevo (`xsmtpsib-...`) |

> Habilitar o custom SMTP sobe o limite para ~30 emails/hora.

## 5. Backend (`backend/.env`)
```env
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
SUPABASE_JWT_ISSUER=https://<project-ref>.supabase.co/auth/v1
SUPABASE_JWKS_URL=https://<project-ref>.supabase.co/auth/v1/.well-known/jwks.json
SUPABASE_JWT_AUDIENCE=authenticated
```

Este projeto usa chaves **assimétricas (ES256)** — basta o **JWKS** (a publicação
pública das suas "JWT Signing Keys"), sem nenhum segredo. O backend não usa
HS256: tokens HS256 são recusados.

> Não é necessária nenhuma **secret key** da Supabase no backend: a validação do
> token é feita com a chave **pública** (JWKS + publishable key).

## Multi-device no modo Supabase (produção)

Funciona cross-device (pedir o login num dispositivo e aprovar em outro,
**fora da mesma rede**), desde que os domínios sejam **públicos**:

- **Site URL**: domínio público do frontend (Vercel).
- **Redirect URLs**: `https://<backend-publico>/**` (Railway/Render/Fly) — com o
  `/**` (ver seção 2).
- `NEXT_PUBLIC_API_URL` (na Vercel) aponta para o backend público; **redeploy** após
  alterar, pois variáveis `NEXT_PUBLIC_*` são embutidas no build.
- `FRONTEND_URL` (no backend) aponta para o domínio da Vercel (CORS).

Fluxo: a Supabase envia o link → o link abre o **callback no backend** → o backend
troca o `token_hash` e marca o pedido (selector) como aprovado → a aba de origem
detecta por polling e entra. É o mesmo mecanismo de selector/polling do modo
Backend Python; a Supabase só substitui o envio do email.

> Em **desenvolvimento local / mesma rede**, use o IP da máquina nos mesmos
> campos (Site URL, Redirect URLs com `/**`, `NEXT_PUBLIC_API_URL`,
> `BACKEND_PUBLIC_URL`, `FRONTEND_URL`) — ver
> [Acesso por outro dispositivo na rede](./08-acesso-rede-multidevice.md).
