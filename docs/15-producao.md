# Produção (rodar fora de desenvolvimento)

[← Voltar ao índice](../README.md)

## Backend: dev vs produção

Em desenvolvimento usamos:
```bash
uvicorn app.main:app --reload --port 8000
```
O `--reload` reinicia a cada alteração de arquivo — ótimo para dev, **inadequado
para produção** (processo único, consumo extra, recarga constante).

Para **produção**, rode sem `--reload` e com **múltiplos workers**. O padrão é
Gunicorn gerenciando workers Uvicorn:
```bash
pip install gunicorn
gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 4 --bind 0.0.0.0:8000
```
- `-w 4`: número de workers (regra inicial: `2 × núcleos + 1`).
- O Uvicorn em si **é** um servidor ASGI de produção; o que muda é *como* ele é
  executado (sem reload, múltiplos workers, atrás de um proxy reverso).

Apenas com Uvicorn (sem Gunicorn), também é possível em produção:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Recomendações de produção
- **Proxy reverso** (nginx/Caddy) na frente, terminando TLS (HTTPS).
- `JWT_SECRET` forte e único (ex.: `openssl rand -hex 32`).
- **SMTP** configurado (Brevo) para envio real dos emails de acesso.
- `FRONTEND_URL` e `BACKEND_PUBLIC_URL` com os domínios reais.
- Redirect URLs e template de email atualizados no painel da Supabase.
- Migrations aplicadas com `alembic upgrade head` no deploy.
- **SQLite**: garanta um volume persistente (ver
  [Decisões técnicas](./14-decisoes-tecnicas.md)); para concorrência alta,
  considere Postgres (basta trocar a `DATABASE_URL`).

## Frontend

```bash
npm run build      # build otimizado de produção
npm run start      # serve o build (Next.js) — porta 3000 por padrão
```
Defina as variáveis `NEXT_PUBLIC_*` no ambiente de build/runtime. Hospedagens como
Vercel detectam o Next automaticamente.

## Docker (stack completa)

O repositório traz `docker-compose.yml` na raiz e um `Dockerfile` em cada serviço
(`backend/` e `frontend/`). O compose sobe três contêineres — **backend**,
**frontend** e **redis** — já conectados (o `REDIS_URL` é injetado no backend, o
que ativa tokens efêmeros, rate limit e realtime entre réplicas).

```bash
# Na raiz do projeto
docker compose up --build
```

- Backend em `http://localhost:8000`, frontend em `http://localhost:3000`.
- O backend cria as tabelas no startup; para um banco versionado use
  `alembic upgrade head` (ver [Rodar o backend](./06-rodar-backend.md)).
- Ajuste as variáveis de ambiente (SMTP, Supabase, URLs) no `docker-compose.yml`
  ou via arquivo `.env` antes de subir em um ambiente real.
- Para escalar o backend em múltiplas réplicas, o Redis garante o fan-out do
  realtime entre elas (ver [Redis: tokens, rate limit e realtime](./05-redis-realtime.md)).

## Email em produção (atenção a SMTP bloqueado)

Algumas hospedagens (ex.: **Railway**) **bloqueiam conexões SMTP de saída**
(portas 25/465/587) por padrão. Nesses casos o envio por SMTP falha com timeout.

Solução: use a **API HTTP do Brevo**, que vai por `https` (porta 443) e não é
bloqueada. Defina `BREVO_API_KEY` (Brevo → SMTP & API → API Keys) e um
`SMTP_FROM` verificado; quando a API key existe, o backend a usa no lugar do SMTP
automaticamente. Em desenvolvimento local, o SMTP normal continua funcionando.

> Falhas de envio de email não derrubam o login: o pedido é criado mesmo assim e
> a resposta indica `email_sent: false`. Em produção, os códigos nunca voltam no
> corpo (falha fechada) — então um canal de email funcionando é obrigatório.
