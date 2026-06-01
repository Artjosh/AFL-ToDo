# ToDo AFL — Desafio Técnico Fullstack

Aplicação de tarefas **colaborativa, estilo Trello/Jira** (board Kanban com
drag-and-drop, projetos aninhados e compartilhamento entre usuários), com
**autenticação passwordless (magic link + OTP)**, **backend Python (FastAPI)**
como fonte de verdade das tarefas e **frontend Next.js (TypeScript + TailwindCSS)**
atuando como **BFF** (o token de sessão vive em cookie httpOnly, nunca no browser).

## Aderência ao desafio (e onde fomos além)

O desafio pedia: API + frontend de to-do com **CRUD de tarefas** (`id, titulo,
descricao, status, data_criacao`), **autenticação JWT (cadastro e login)**, **cada
usuário só vê suas tarefas**, **persistência em SQLite** e **README detalhado**.
Tudo isso está entregue:

- **CRUD completo** de tarefas com todos os campos exigidos. ✅
- **JWT + cadastro + login**: o login é **passwordless** (magic link + código OTP).
  O **cadastro continua existindo** — ele acontece de forma integrada **no primeiro
  acesso** (ao confirmar o link/código, a conta é criada automaticamente). E o
  **JWT continua sendo o mecanismo de sessão** (emitido pelo backend após a
  confirmação). Ou seja: cadastro, login e JWT estão presentes — apenas sem senha,
  o que **elimina uma classe inteira de riscos** (vazamento/reuso de senhas,
  brute force). É uma melhoria de segurança, não uma ausência de requisito. ✅
- **Isolamento por usuário** validado no backend a cada requisição. ✅
- **SQLite** como persistência. ✅
- **README + documentação** detalhada (abaixo). ✅

**Implementações complementares (além do mínimo):** board Kanban com
drag-and-drop, **projetos** com board aninhado, **compartilhamento** com
**permissões por membro** (mover projeto, mover/gerenciar tarefas), **política de
remoção** de membro, **alertas por email** de eventos de tarefa, **realtime**
(WebSocket + Redis Pub/Sub), **multi-dispositivo** (clicar o link em outro
aparelho), **modo Supabase Auth** opcional, **padrão BFF** (cookie httpOnly +
proxy + ticket de WebSocket) e **104 testes de backend + 21 de frontend + 16 E2E**.

Destaques:
- **Board Kanban** (Pendente / Em andamento / Concluída) com arrastar-e-soltar.
- **Projetos**: agrupam tarefas; aparecem como card na lista e expandem num board próprio, com **status** próprio.
- **Compartilhamento + permissões por membro**: defina quem pode mover o projeto,
  mover/criar/editar/excluir tarefas e quem recebe **alertas por email**.
- **Política de remoção** de membro (revogar acesso ou manter como dono das tarefas).
- **Login sem senha** multi-dispositivo (link + código de 6 dígitos), com dois
  modos: Backend Python ou Python + Supabase Auth.
- **Realtime** (opcional, via Redis): o board atualiza ao vivo quando outro membro mexe.
- **Padrão BFF**: o token de sessão fica em cookie httpOnly (fora do alcance do JS).
- Acesso por **membership** (criador, atribuído ou membro do projeto), validado no backend.

## Início rápido

```bash
# Backend (em backend/)
python -m venv .venv && .\.venv\Scripts\Activate.ps1   # Win
pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --port 8000              # http://localhost:8000

# Frontend (em frontend/)
npm install
copy .env.example .env.local
npm run dev                                            # http://localhost:3000
```

Sem SMTP configurado, o backend roda em **modo dev**: o link e o código de acesso
aparecem na própria tela. Suba o backend antes do frontend.

## Documentação

A documentação detalhada fica na pasta [`docs/`](./docs), separada por tema e em
ordem de leitura (entender → configurar → rodar → como funciona → operar):

| # | Documento | Conteúdo |
|---|-----------|----------|
| 01 | [Visão geral](./docs/01-visao-geral.md) | O que o sistema faz, modos de auth e tecnologias |
| 02 | [Estrutura do projeto](./docs/02-estrutura.md) | Árvore de pastas e arquivos comentada |
| 03 | [Configuração e `.env`](./docs/03-configuracao-env.md) | Variáveis de backend e frontend (inclui Brevo) |
| 04 | [Configurar a Supabase](./docs/04-configurar-supabase.md) | Chaves, redirect URLs e template de email |
| 05 | [Redis: tokens, rate limit e realtime](./docs/05-redis-realtime.md) | Camada opcional de aceleração e board ao vivo |
| 06 | [Como rodar o backend](./docs/06-rodar-backend.md) | venv, dependências, migrations Alembic, servidor |
| 07 | [Como rodar o frontend](./docs/07-rodar-frontend.md) | Dependências, dev, build e acesso na rede |
| 08 | [Acesso por outro dispositivo na rede](./docs/08-acesso-rede-multidevice.md) | Rodar e testar multi-device na mesma rede Wi-Fi |
| 09 | [Autenticação](./docs/09-autenticacao.md) | Passwordless, magic link + OTP, multi-device, tour guiado |
| 10 | [Projetos e colaboração](./docs/10-projetos-colaboracao.md) | Board Kanban, projetos aninhados, compartilhamento e atribuídos |
| 11 | [Endpoints](./docs/11-endpoints.md) | Rotas de auth, tarefas e projetos + exemplos curl |
| 12 | [Painel admin do SQLite](./docs/12-painel-admin-sqlite.md) | Visualizar os dados do banco em dev (sqlite-web) |
| 13 | [Segurança](./docs/13-seguranca.md) | CORS, JWT, ownership, validação de token |
| 14 | [Decisões técnicas](./docs/14-decisoes-tecnicas.md) | Escolhas de arquitetura, SQLite e deploy |
| 15 | [Produção](./docs/15-producao.md) | Como rodar fora de desenvolvimento (workers, build) |
| — | [Testes automatizados](./tests/README.md) | pytest (backend), vitest (frontend) e Playwright (E2E) |

## Stack

- **Backend:** FastAPI · SQLAlchemy 2 · Alembic · Pydantic v2 · PyJWT · SQLite · Redis (opcional)
- **Frontend:** Next.js 15 (App Router) · React 19 · TypeScript · TailwindCSS · @supabase/ssr
