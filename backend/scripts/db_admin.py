"""Painel web para inspecionar o banco SQLite (ferramenta de desenvolvimento).

Sobe o sqlite-web apontando para o app.db do backend, em modo somente-leitura
por padrão (seguro para apenas visualizar dados).

Uso (a partir de backend/, com a venv ativada):
    python scripts/db_admin.py                 # somente leitura, porta 8081
    python scripts/db_admin.py --edit          # permite editar (cuidado)
    python scripts/db_admin.py --port 9000      # outra porta

Requer: pip install -r requirements-dev.txt
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Painel SQLite (sqlite-web)")
    parser.add_argument("--port", default="8081", help="Porta (padrão 8081)")
    parser.add_argument(
        "--edit",
        action="store_true",
        help="Permite edição (sem --edit, abre em somente-leitura).",
    )
    parser.add_argument(
        "--db",
        default=str(BACKEND_DIR / "app.db"),
        help="Caminho do banco (padrão: backend/app.db)",
    )
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"Banco não encontrado: {db_path}")
        print("Rode 'alembic upgrade head' (em backend/) para criar as tabelas.")
        return 1

    cmd = [
        sys.executable,
        "-m",
        "sqlite_web",
        str(db_path),
        "--port",
        str(args.port),
        "--no-browser",
    ]
    if not args.edit:
        cmd.append("--read-only")

    mode = "edição" if args.edit else "somente leitura"
    print(f"Painel SQLite em http://127.0.0.1:{args.port}  ({mode})")
    print("Ctrl+C para encerrar.")
    return subprocess.call(cmd, cwd=str(BACKEND_DIR), env=os.environ.copy())


if __name__ == "__main__":
    raise SystemExit(main())
