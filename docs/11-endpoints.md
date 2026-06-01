# Endpoints principais

[← Voltar ao índice](../README.md)

Base URL: `http://localhost:8000` — Swagger interativo em `/docs`.

## Autenticação (passwordless: magic link + OTP)

| Método | Rota                              | Descrição                                              | Auth |
|--------|-----------------------------------|--------------------------------------------------------|------|
| POST   | `/auth/magic-link`                | (local) Solicita link + código OTP; devolve `selector` | —  |
| GET    | `/auth/confirm?token=...`         | (local) Alvo do link; aprova o login (qualquer device) | —  |
| POST   | `/auth/verify-otp`                | (local) Valida o código de 6 dígitos                    | —  |
| POST   | `/auth/supabase/start`            | (supabase) Cria pedido para polling cross-device        | —  |
| GET    | `/auth/supabase/callback`         | (supabase) Troca token_hash por sessão e aprova login   | —  |
| POST   | `/auth/login-status?selector=...` | Polling; troca o selector pela sessão quando aprovado   | —  |
| POST   | `/auth/supabase/sync`             | Espelha/atualiza o usuário Supabase no SQLite           | Bearer (Supabase) |
| POST   | `/auth/ws-ticket`                 | Emite um ticket efêmero (JWT `type=ws`, ~60s) p/ o WebSocket | Bearer |
| GET    | `/auth/me`                        | Dados do usuário autenticado (qualquer modo)            | Bearer |

> **Acesso via BFF.** No app real, o **browser não chama estas rotas
> diretamente**: ele fala com o servidor do Next (same-origin), que injeta o
> `Authorization: Bearer` a partir do cookie httpOnly. Ver a seção
> [Rotas do BFF](#rotas-do-bff-next) abaixo. As tabelas acima são a API do
> FastAPI (fonte de verdade), úteis para testes diretos via `curl`/Swagger.

## Tarefas (todas exigem `Authorization: Bearer <token>`)

| Método | Rota           | Descrição                          |
|--------|----------------|------------------------------------|
| GET    | `/tasks`       | Lista tarefas acessíveis (criador/atribuído/projeto) |
| GET    | `/tasks?standalone=true` | Apenas tarefas soltas (sem projeto) |
| GET    | `/tasks?project_id=N` | Tarefas do projeto N (se tiver acesso) |
| POST   | `/tasks`       | Cria tarefa (opcional `project_id`) |
| GET    | `/tasks/{id}`  | Detalha uma tarefa (se tiver acesso) |
| PATCH  | `/tasks/{id}`  | Atualiza título/descrição/status/posição/projeto |
| POST   | `/tasks/reorder` | Reordena uma coluna (ids na ordem + status); drag-and-drop |
| DELETE | `/tasks/{id}`  | Exclui a tarefa                    |
| POST   | `/tasks/{id}/assignees` | Atribui uma pessoa (por email) |
| DELETE | `/tasks/{id}/assignees/{user_id}` | Remove a atribuição |

> **Status válidos:** `pendente`, `em_andamento`, `concluida`.

## Projetos e membros (compartilhamento)

| Método | Rota           | Descrição                          |
|--------|----------------|------------------------------------|
| GET    | `/projects`    | Lista projetos do usuário (dono ou membro) |
| POST   | `/projects`    | Cria um projeto                    |
| GET    | `/projects/{id}` | Detalha o projeto com as tarefas (board) |
| PATCH  | `/projects/{id}` | Atualiza nome/descrição (dono); `status` (dono ou membro com permissão); `removed_member_policy` e `owner_receives_alerts` (dono) |
| DELETE | `/projects/{id}` | Exclui o projeto (só dono)       |
| POST   | `/projects/{id}/members` | Adiciona membro por email (só dono) |
| PATCH  | `/projects/{id}/members/{user_id}` | Configura permissões do membro (só dono): `can_move_project`, `can_move_tasks`, `can_manage_tasks`, `receives_alerts` |
| DELETE | `/projects/{id}/members/{user_id}` | Remove membro (só dono); aplica a política de remoção |

> **Permissões e alertas:** as ações de tarefa (mover/criar/editar/excluir) e
> mover o status do projeto respeitam as permissões por membro. Criar uma tarefa
> ou mudar seu status dispara **email de alerta** (backend Python) para o dono e
> membros marcados com `receives_alerts`. Ver
> [Projetos e colaboração](./10-projetos-colaboracao.md).

## Exemplo — login passwordless no modo dev (curl)

```bash
# 1) Solicita o link + código (modo dev devolve dev_magic_url e dev_otp_code)
curl -X POST http://localhost:8000/auth/magic-link \
  -H "Content-Type: application/json" \
  -d '{"email":"voce@exemplo.com"}'

# 2a) Abra a dev_magic_url no navegador (ou: curl <dev_magic_url>)
#     e faça o polling para obter a sessão:
curl -X POST "http://localhost:8000/auth/login-status?selector=<SELECTOR>"

# 2b) OU valide o código de 6 dígitos diretamente:
curl -X POST http://localhost:8000/auth/verify-otp \
  -H "Content-Type: application/json" \
  -d '{"selector":"<SELECTOR>","code":"123456"}'

# 3) Use o access_token devolvido para criar uma tarefa
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{"titulo":"Estudar FastAPI","status":"pendente"}'
```

## Rotas do BFF (Next)

Estas rotas rodam **no servidor do Next** (não no FastAPI). São o que o browser de
fato chama (same-origin). Elas leem/gravam o cookie httpOnly de sessão e repassam
ao backend Python. Ver [Segurança → Padrão BFF](./13-seguranca.md).

| Método | Rota                         | Descrição                                                      |
|--------|------------------------------|----------------------------------------------------------------|
| ANY    | `/api/py/*`                  | Proxy para o FastAPI; injeta `Authorization: Bearer` do cookie |
| POST   | `/api/auth/login?step=otp`   | (local) Valida OTP no servidor e grava o cookie de sessão      |
| POST   | `/api/auth/login?step=poll`  | (local) Polling; ao aprovar, grava o cookie de sessão          |
| POST   | `/api/auth/session`          | (supabase) Recebe o token, valida e grava o cookie httpOnly    |
| GET    | `/api/auth/session`          | Restaura a sessão a partir do cookie (devolve o usuário)       |
| DELETE | `/api/auth/session`          | Logout: limpa os cookies                                       |
| POST   | `/api/auth/ws-ticket`        | Troca o cookie por um ticket efêmero para o WebSocket          |

> O token de sessão **nunca** é devolvido ao browser por nenhuma destas rotas —
> ele permanece apenas no cookie `httpOnly`.
