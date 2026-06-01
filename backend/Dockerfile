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

# Porta: usa a injetada pelo ambiente (Railway/Render definem $PORT); 8000 local.
ENV PORT=8000
EXPOSE 8000

# Aplica migrations e sobe o servidor escutando na porta do ambiente ($PORT).
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2"]
