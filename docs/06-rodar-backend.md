# Como rodar o backend

[← Voltar ao índice](../README.md)

> Pré-requisitos: **Python 3.11+** (testado em 3.12).

A partir da pasta `backend/`:

## 1. Criar e ativar o ambiente virtual

**Windows (PowerShell):**
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Linux / macOS:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
```

## 2. Instalar dependências
```bash
pip install -r requirements.txt
```

## 3. Configurar variáveis de ambiente
```bash
# Windows
Copy-Item .env.example .env
# Linux / macOS
cp .env.example .env
```
Para o **modo local em dev**, o padrão já funciona (sem SMTP, o link + código
aparecem na tela). Troque o `JWT_SECRET` em produção. Detalhes de todas as
variáveis em [Configuração e .env](./03-configuracao-env.md).

## 4. Rodar as migrations (cria as tabelas)
```bash
alembic upgrade head
```

## 5. Subir o servidor

> ⚠️ Rode **de dentro da pasta `backend/`** (onde fica o pacote `app/`). Rodar de
> outro diretório — por exemplo `tests/backend/` — causa
> `ModuleNotFoundError: No module named 'app'`.

```bash
# Em backend/, com a venv ativada:
uvicorn app.main:app --reload --port 8000
```

- API: <http://localhost:8000>
- Swagger (docs interativa): <http://localhost:8000/docs>

### Acessível na rede (outro dispositivo / celular)

Para que outro aparelho na mesma rede alcance o backend, escute em todas as
interfaces com `--host 0.0.0.0`:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Isso é só um dos 4 ajustes alinhados ao mesmo IP — o passo a passo completo
(frontend na rede, `NEXT_PUBLIC_API_URL`, `FRONTEND_URL`/`BACKEND_PUBLIC_URL`)
está em [Acesso por outro dispositivo na rede](./08-acesso-rede-multidevice.md).

## Migrations com Alembic

As migrations ficam em `backend/alembic/versions/`. A URL do banco é lida das
configurações da aplicação (`DATABASE_URL`).

A partir de `backend/` (com a venv ativada):
```bash
alembic upgrade head                               # aplica todas as migrations
alembic revision --autogenerate -m "mensagem"      # cria nova migration
alembic downgrade -1                               # desfaz a última
```

> O `env.py` usa `render_as_batch=True`, necessário para o SQLite suportar
> `ALTER TABLE` em migrations futuras.
