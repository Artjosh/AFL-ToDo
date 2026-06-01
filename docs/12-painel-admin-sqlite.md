# Painel admin do SQLite (desenvolvimento)

[← Voltar ao índice](../README.md)

Para inspecionar/visualizar os dados do banco (usuários, tarefas, projetos,
membros, atribuídos) existe um painel web baseado em **sqlite-web**. É uma
ferramenta de **desenvolvimento** — não faz parte da API nem deve ser exposta em
produção.

## Instalação

```bash
cd backend
.\.venv\Scripts\Activate.ps1        # Windows
pip install -r requirements-dev.txt # inclui o sqlite-web
```

## Uso

A partir de `backend/` (com a venv ativada):

```bash
# Somente leitura (recomendado para apenas visualizar) — porta 8081
python scripts/db_admin.py

# Permitir edição (cuidado: altera o banco direto)
python scripts/db_admin.py --edit

# Outra porta / outro banco
python scripts/db_admin.py --port 9000
python scripts/db_admin.py --db ./app.db
```

Acesse <http://127.0.0.1:8081>. O painel mostra todas as tabelas
(`users`, `tasks`, `projects`, `project_members`, `task_assignees`,
`login_tokens`), permite navegar pelos registros, ver o schema e rodar consultas.

> Por padrão abre em **somente leitura** (`--read-only`), seguro para inspeção.
> Use `--edit` apenas se realmente quiser alterar dados manualmente.

## Alternativas

- **Swagger** (<http://localhost:8000/docs>) — para exercitar a API.
- **DB Browser for SQLite** (app desktop) ou a extensão *SQLite* do VS Code, se
  preferir abrir o arquivo `backend/app.db` diretamente.
- No modo Supabase, os **usuários de auth** ficam no painel da Supabase
  (Authentication → Users) — as tarefas continuam no SQLite.
