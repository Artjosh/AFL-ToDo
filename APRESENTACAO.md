# ToDo AFL — To-do Colaborativo Fullstack

Aplicação de lista de tarefas estilo **Trello/Jira**, com autenticação sem senha,
backend Python como fonte de verdade e frontend Next.js como camada segura (BFF).

**Stack:** FastAPI · SQLite · Next.js 15 · TypeScript · TailwindCSS · Redis (opcional)

> Desafio técnico fullstack — entregue com melhorias de segurança e arquitetura.
> Documentação completa em `README.md` e na pasta `docs/`.

---

## O Desafio

O que foi pedido:

- API + frontend de **to-do** com CRUD de tarefas (`id, titulo, descricao, status, data_criacao`)
- **Autenticação JWT** (cadastro e login)
- Cada usuário acessa **apenas as próprias tarefas**
- Persistência em **SQLite**
- **README** com passo a passo

Avaliação: organização, boas práticas, clareza, documentação, usabilidade e
**implementações complementares**.

> Detalhes da aderência: `README.md` → seção "Aderência ao desafio".

---

## A Entrega (visão geral)

Tudo o que foi pedido — e bem além:

- **Board Kanban** (Pendente / Em andamento / Concluída) com drag-and-drop
- **Projetos**: agrupam tarefas, viram um board aninhado
- **Colaboração** com permissões finas por membro
- **Login sem senha** (magic link + código OTP), multi-dispositivo
- **Realtime**: o board atualiza ao vivo quando outro membro mexe
- **Alertas por email** de eventos de tarefa

> Visão geral: `docs/01-visao-geral.md` · Estrutura: `docs/02-estrutura.md`

---

## Autenticação sem senha (e por quê)

Login **passwordless**: o usuário informa o email e recebe um **link** + um
**código de 6 dígitos**. O primeiro acesso cria a conta automaticamente.

- **Cadastro, login e JWT continuam existindo** — só que sem senha
- Elimina uma classe inteira de riscos: vazamento, reuso e força bruta de senhas
- Funciona **multi-dispositivo**: peça no PC, confirme no celular (via polling)
- Dois modos: **Backend Python** (próprio) ou **Python + Supabase Auth**

> Como funciona: `docs/09-autenticacao.md` · Supabase: `docs/04-configurar-supabase.md`

---

## Arquitetura: Python como fonte de verdade + BFF

O backend Python é a **autoridade**; o Next.js é a **camada de borda segura**.

- **FastAPI** valida todo request e é dono dos dados (SQLite)
- **Next.js como BFF**: o token de sessão vive em **cookie httpOnly**, nunca no
  JavaScript do navegador
- O browser fala só com o Next (same-origin); o Next injeta o token e repassa ao Python
- Mesmo com XSS, não há token de sessão acessível para roubo

> Segurança e BFF: `docs/13-seguranca.md` · Decisões: `docs/14-decisoes-tecnicas.md`

---

## Colaboração com permissões finas

Um **projeto** agrupa tarefas, vira um card no board (com **status próprio**,
arrastável entre colunas) e é a unidade de compartilhamento. O dono configura,
**por membro**:

- Quem pode **mover o projeto** entre status
- Quem pode **mover tarefas** (drag-and-drop)
- Quem pode **criar/editar/excluir** tarefas
- Quem **recebe emails** de alerta
- Política ao remover alguém: **revogar acesso** ou **manter como dono** das tarefas

Todo card mostra o **criador** (sempre) e os **atribuídos** como avatares. Atribuir
alguém compartilha a tarefa — funciona até em tarefas fora de projeto.

> Projetos e colaboração: `docs/10-projetos-colaboracao.md`

---

## Camada Redis (opcional) + Realtime

SQLite continua sendo a **fonte de verdade**. O Redis é uma camada de aceleração
**opcional**, com fallback gracioso (sem ele, tudo funciona).

- **Tokens de login efêmeros** com TTL automático (tira o polling do banco)
- **Rate limiting** anti-spam no envio de magic link
- **Realtime** via Pub/Sub + WebSocket: board ao vivo entre membros

> Redis e realtime: `docs/05-redis-realtime.md`

---

## Segurança em primeiro lugar

Decisões pensadas para produção:

- Sessão **JWT** com expiração; magic link/OTP de uso único e com tentativas limitadas
- **Acesso por membership** validado no backend (nunca confia em id do frontend)
- Token Supabase validado por **chave pública (JWKS)** — sem segredos no backend
- **Falha fechada**: em produção, segredos nunca vão na resposta e o app recusa
  subir sem SMTP ou com `JWT_SECRET` fraco

> Segurança: `docs/13-seguranca.md` · Configuração: `docs/03-configuracao-env.md`

---

## Qualidade: testes automatizados

Três camadas, seguindo a pirâmide de testes:

- **Backend (pytest):** 104 testes — auth, CRUD, permissões, alertas, Redis, realtime
- **Frontend (vitest):** 21 testes — cliente de API (BFF), componentes, regressões
- **E2E (Playwright):** 16 testes — fluxos completos (UI + HTTP + banco)

Cobre os 3 níveis: interface, API e persistência.

> Testes: `tests/README.md` · Produção e Docker: `docs/15-producao.md`

---

## Como rodar (resumo)

```bash
# Backend (em backend/)
python -m venv .venv && pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend (em frontend/)
npm install && npm run dev   # http://localhost:3000
```

Sem SMTP, o link e o código aparecem na própria tela (modo dev).

> Passo a passo: `docs/06-rodar-backend.md` · `docs/07-rodar-frontend.md`
> Acesso na rede / multi-device: `docs/08-acesso-rede-multidevice.md`
