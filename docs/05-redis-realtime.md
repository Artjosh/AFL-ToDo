# Redis: tokens efêmeros, rate limit e realtime

[← Voltar ao índice](../README.md)

O Redis é **opcional**. Sem ele, o app funciona normalmente (fallback no banco /
recursos desativados). Com ele, ganha três coisas:

## 1. Tokens de login efêmeros (com TTL)

Os pedidos de login (magic link + OTP) são dados **voláteis** — expiram em minutos
e são consultados em polling a cada poucos segundos. Quando há Redis, eles ficam
**no Redis com expiração automática** (`app/services/login_tokens.py`), tirando do
SQLite o tráfego intenso do polling multi-device. Sem Redis, caem na tabela
`login_tokens` (comportamento idêntico, só que no banco).

## 2. Rate limiting

`POST /auth/magic-link` é protegido contra spam por email e por IP
(`app/core/rate_limit.py`), usando contadores com janela no Redis. Limites:
`RATE_LIMIT_MAX` solicitações por `RATE_LIMIT_WINDOW_SECONDS`. Sem Redis, o rate
limit é um no-op (não bloqueia) — adequado para dev.

## 3. Realtime do board (WebSocket + Pub/Sub)

Quando um membro cria/move/exclui uma tarefa, os outros membros conectados veem a
mudança **ao vivo**, sem recarregar. Funciona assim:

- O frontend abre um WebSocket em `/ws/board?token=...&project_id=...`
  (`lib/realtime.ts`). O backend valida o token e o acesso ao escopo.
- Ao mudar uma tarefa, o backend publica um evento num tópico
  (`project:<id>` ou `standalone:<user_id>`).
- **Com Redis**: o fan-out usa Pub/Sub, então funciona entre **várias réplicas**
  do backend (um cliente na réplica A recebe evento publicado na B).
- **Sem Redis**: usa um broadcaster em memória (single-process), suficiente para
  dev/instância única.

## Configuração

No `backend/.env`:
```env
# Vazio = desativado (fallback no banco, sem rate limit/realtime distribuído).
REDIS_URL=redis://localhost:6379/0
RATE_LIMIT_MAX=5
RATE_LIMIT_WINDOW_SECONDS=60
```

Com Docker, o `docker-compose.yml` já sobe um Redis e injeta o `REDIS_URL` no
backend automaticamente.

## Por que não trocamos o SQLite

O SQLite continua sendo a **fonte de verdade** das tarefas (decisão da equipe).
O Redis é uma **camada de aceleração/realtime**, não um banco — ele guarda só
dados efêmeros (tokens, contadores) e mensagens de Pub/Sub. Nada de dado durável
vive só no Redis.
