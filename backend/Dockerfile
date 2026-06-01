# Backend FastAPI (produção-ish): Uvicorn com workers, sem --reload.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Dependências primeiro (cache de camada)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Código
COPY . .

# O banco SQLite fica em /data (montado como volume persistente).
ENV DATABASE_URL=sqlite:////data/app.db

EXPOSE 8000

# Aplica migrations e sobe o servidor (2 workers como exemplo).
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2"]
