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

**Site URL** (campo único, base do projeto):
```
http://192.168.100.163:3000
```

**Redirect URLs** (allowlist — adicione todas):
```
http://192.168.100.163:8000/auth/supabase/callback
http://localhost:8000/auth/supabase/callback
http://192.168.100.163:3000
http://localhost:3000
```

Por que cada uma:
- `.../:8000/auth/supabase/callback` (IP + localhost) — **alvo do link do email** no
  fluxo cross-device. O frontend monta o `emailRedirectTo` como
  `NEXT_PUBLIC_API_URL/auth/supabase/callback?selector=...`; como o seu
  `NEXT_PUBLIC_API_URL` é `http://192.168.100.163:8000`, **a do IP é a essencial**
  (a de `localhost` cobre o teste na própria máquina).
- `.../:3000` (IP + localhost) — fallback de mesmo-device: sem pedido de polling, o
  backend redireciona para `FRONTEND_URL/login?supabase=confirmed`.

> **Troque `192.168.100.163` pelo IP da sua máquina** (e, em produção, pelo domínio
> real). O IP da rede local **não é alcançável de fora** dela: para multi-device
> real no modo Supabase, use uma URL pública (deploy ou túnel) — ver
> [Acesso por outro dispositivo na rede](./08-acesso-rede-multidevice.md). No modo
> **Backend Python** isso não se aplica.

Ajuste para as URLs de produção quando publicar.

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
> usa `{{ .RedirectTo }}&token_hash={{ .TokenHash }}&type=email`. Assim os dois
> modos enviam um email visualmente idêntico. O app aceita as duas vias: clicar o
> link ou digitar o código.

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

## Observação sobre multi-device no modo Supabase

O link do email aponta para `http://localhost:8000/auth/supabase/callback`.
Clicar **no mesmo computador** funciona. Clicar **em outro dispositivo** (ex.:
celular) não alcança o `localhost` da sua máquina — para multi-device real no
modo Supabase é preciso uma **URL pública do backend** (deploy ou um túnel como
`ngrok`/`cloudflared`), e atualizar a Redirect URL + `BACKEND_PUBLIC_URL` para
essa URL. O modo **Backend Python** não tem essa limitação (o link é do próprio
backend e o polling é independente).
