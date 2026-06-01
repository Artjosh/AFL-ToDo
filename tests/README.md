# Testes automatizados

Três camadas de testes, seguindo a pirâmide (muitos testes rápidos na base, poucos
E2E no topo):

```
tests/
├── backend/    # pytest — unit + integração da API (rápido)
├── frontend/   # vitest — unit das libs e componentes (rápido)
└── e2e/        # playwright — fluxos completos UI + HTTP + banco (lento)
```

## 1. Backend (pytest)

Cobre rotas de auth (magic link, OTP, polling, callback Supabase, ticket de
WebSocket), CRUD de tarefas, **projetos e compartilhamento (membros)**,
**permissões por membro** (mover projeto, mover/gerenciar tarefas, alertas),
**política de remoção** (revogar/manter) e **alertas por email** (destinatários),
**atribuídos (assignees)**, **reordenação do board (drag-and-drop)**, **caminho
Redis** (tokens efêmeros + rate limit, com fakeredis), **realtime** (broadcaster +
auth do WebSocket), acesso por membership, validação, edge cases/regressão e o
vínculo de contas por email entre os modos. (104 testes)

```bash
cd backend
.\.venv\Scripts\Activate.ps1            # Windows (ou: source .venv/bin/activate)
pip install -r requirements-dev.txt     # instala pytest (uma vez)
cd ../tests/backend
python -m pytest                        # roda os testes
python -m pytest --cov=app --cov-report=term-missing   # com cobertura
```

> Cada teste usa um SQLite isolado (tmp). A verificação de assinatura do token
> Supabase é mockada (não depende de rede).

## 2. Frontend (vitest)

Cobre `lib/toast-state` (mostrado/clicado/anti-spam), `lib/api` (cliente HTTP do
BFF, mockando fetch), a **estabilidade do contexto de toast** (regressão) e
componentes — incluindo o `BoardCard` (avatar do **criador** sempre visível +
atribuídos, sem duplicar).

```bash
cd frontend
npm install            # instala vitest etc. (uma vez)
npm test               # roda os testes
npm run test:cov       # com cobertura
```

## 3. E2E (Playwright)

Sobe **backend + frontend automaticamente** (portas 8100/3100, banco `e2e.db`
dedicado, modo dev sem SMTP) e testa pelo navegador. Um único teste E2E valida as
três camadas ao mesmo tempo: **UI** (cliques/telas), **HTTP** (API) e **banco**
(consulta o SQLite via `better-sqlite3`).

Cobre: tour guiado, login via OTP, CRUD de tarefas refletido no banco, isolamento
entre usuários, **login multi-dispositivo** (link clicado em "outro device"
confirma a aba de origem por polling), **criação de projetos**, **board do projeto**,
**compartilhamento** (adicionar membro), **permissões por membro** (membro sem
"mover tarefas" não arrasta os cards), **mover o próprio projeto entre colunas**
(status do projeto), **atribuição de pessoas** a tarefas, **drag-and-drop** (mover
entre colunas e reordenar dentro da coluna, sem flash de "carregando") e
**realtime** (tarefa criada por um membro aparece ao vivo no board de outro). (16 testes)

```bash
cd tests/e2e
npm install                 # instala Playwright + better-sqlite3 (uma vez)
npx playwright install chromium   # baixa o navegador (uma vez)
npm test                    # roda headless
npm run test:headed         # roda com o navegador visível
npm run report              # abre o último relatório HTML
```

> Pré-requisito: a venv do backend deve existir em `backend/.venv` com as
> dependências instaladas (o Playwright usa o Python de lá para subir a API).

## O que NÃO é coberto automaticamente

- **Envio real de email (SMTP/Brevo)** e o **fluxo Supabase end-to-end pela UI**:
  dependem de caixa de email e de rate limits do provedor. Foram validados
  manualmente e por testes de backend (token Supabase real → validação JWKS →
  espelhamento). O modo Supabase multi-device também exige o template/redirect
  configurados no painel da Supabase.
