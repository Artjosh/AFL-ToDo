# ToDo AFL — To-do Colaborativo Fullstack

Aplicação de lista de tarefas estilo **Trello/Jira**, com autenticação sem senha,
backend Python como fonte de verdade e frontend Next.js como camada segura (BFF).

**Stack:** FastAPI · SQLite · Next.js 15 · TypeScript · TailwindCSS · Redis (opcional)

> Documentação completa em `README.md` e na pasta `docs/`.

---

## O que o sistema faz

- **CRUD de tarefas** com `id`, `titulo`, `descricao`, `status` e `data_criacao`
- **Autenticação** sem senha (magic link + código OTP), com sessão **JWT**
- Cada usuário acessa **apenas as tarefas a que tem acesso**
- Persistência em **SQLite**
- Interface estilo **Trello/Jira** com board Kanban

> Visão geral: `docs/01-visao-geral.md` · Estrutura: `docs/02-estrutura.md`

---

## Board Kanban e projetos

- Três colunas (Pendente / Em andamento / Concluída) com **drag-and-drop**
- **Projetos** agrupam tarefas e viram um board aninhado
- O card do projeto também tem **status próprio** e arrasta entre colunas
- Cada card mostra o **criador** e as **pessoas atribuídas** (avatares)

> Projetos e colaboração: `docs/10-projetos-colaboracao.md`

---

## Autenticação sem senha

O usuário informa o email e recebe um **link** + um **código de 6 dígitos**.

- O **cadastro acontece no primeiro acesso**: ao confirmar o link ou o código, a
  conta é criada
- A sessão usa **JWT**, emitido pelo backend após a confirmação
- Funciona **multi-dispositivo**: peça o link no PC, confirme no celular
- Dois modos: **Backend Python** (próprio) ou **Python + Supabase Auth**

> Como funciona: `docs/09-autenticacao.md` · Supabase: `docs/04-configurar-supabase.md`

---

## Arquitetura: Python + BFF

O backend Python é a fonte de verdade; o Next.js é a camada de borda.

- **FastAPI** valida todo request e é dono dos dados (SQLite)
- **Next.js como BFF**: o token de sessão fica num **cookie httpOnly**
- O **navegador anexa esse cookie automaticamente** nas requisições ao Next
  (same-origin); o **JavaScript da página não consegue ler o cookie** (é o que o
  `httpOnly` garante)
- O Next lê o cookie no servidor, injeta o token como `Bearer` e repassa ao Python

> Mesmo em caso de XSS, o token não pode ser **lido/exfiltrado** pelo JavaScript.

> Como funciona: `docs/13-seguranca.md` · Decisões: `docs/14-decisoes-tecnicas.md`

---

## Colaboração e permissões

Um **projeto** é a unidade de compartilhamento. O dono configura, **por membro**:

- Quem pode **mover o projeto** entre status
- Quem pode **mover tarefas** (drag-and-drop)
- Quem pode **criar/editar/excluir** tarefas
- Quem **recebe emails** de alerta de criação/mudança de status
- Política ao remover alguém: **revogar acesso** ou **manter como dono** das tarefas

Atribuir uma pessoa a uma tarefa dá acesso a ela — inclusive em tarefas fora de projeto.

> Projetos e colaboração: `docs/10-projetos-colaboracao.md`

---

## Camada Redis (opcional) e realtime

SQLite é a fonte de verdade. O Redis é uma camada de aceleração opcional, com
fallback (sem ele, tudo funciona).

- **Tokens de login efêmeros** com TTL automático
- **Rate limiting** no envio de magic link
- **Realtime** via Pub/Sub + WebSocket: o board atualiza ao vivo entre membros

> Redis e realtime: `docs/05-redis-realtime.md`

---

## Segurança

- Sessão **JWT** com expiração; magic link/OTP de uso único e tentativas limitadas
- **Acesso por membership** validado no backend (o `user_id` vem do token, nunca do frontend)
- Token Supabase validado por **chave pública (JWKS)**
- Em produção, o backend não expõe segredos na resposta e exige SMTP + `JWT_SECRET` forte

> Segurança: `docs/13-seguranca.md` · Configuração: `docs/03-configuracao-env.md`

---

## Testes automatizados

Três camadas, com CI no GitHub Actions a cada push:

- **Backend (pytest):** 104 testes — auth, CRUD, permissões, alertas, Redis, realtime
- **Frontend (vitest):** 21 testes — cliente de API (BFF), componentes
- **E2E (Playwright):** 16 testes — fluxos completos (UI + HTTP + banco)

> Testes: `tests/README.md` · Produção e Docker: `docs/15-producao.md`

---

## Como rodar

```bash
# Backend (em backend/)
python -m venv .venv && pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend (em frontend/)
npm install && npm run dev   # http://localhost:3000
```

Sem SMTP, o link e o código aparecem na própria tela.

> Passo a passo: `docs/06-rodar-backend.md` · `docs/07-rodar-frontend.md`
> Acesso na rede: `docs/08-acesso-rede-multidevice.md`
