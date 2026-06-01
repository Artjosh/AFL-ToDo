# Como rodar o frontend

[← Voltar ao índice](../README.md)

> Pré-requisitos: **Node.js 18+** (testado em Node 24) e npm.

A partir da pasta `frontend/`:

## 1. Instalar dependências
```bash
cd frontend
npm install
```

## 2. Configurar variáveis de ambiente
O Next lê `.env` ou `.env.local`:
```bash
# Windows
Copy-Item .env.example .env.local
# Linux / macOS
cp .env.example .env.local
```
Para o **modo local**, basta `NEXT_PUBLIC_API_URL`. Para habilitar o **modo
Supabase**, preencha `NEXT_PUBLIC_SUPABASE_URL` e
`NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` (o seletor só habilita a opção Supabase se
essas existirem). Ver [Configuração e .env](./03-configuracao-env.md).

## 3. Rodar em desenvolvimento
```bash
npm run dev          # http://localhost:3000
```

## 4. Rodar acessível na rede (outro dispositivo / celular)

Por padrão o `npm run dev` escuta só em `localhost`, que outros aparelhos **não
alcançam**. Para abrir no celular/outro PC na mesma rede, use a flag `-H 0.0.0.0`:

```bash
npm run dev -- -H 0.0.0.0 -p 3000
```

Isso faz o Next escutar em todas as interfaces (ele imprime o endereço de rede,
ex.: `Network: http://192.168.x.x:3000`). Mas **só a flag não basta** — o backend
também precisa escutar na rede e o frontend precisa apontar para o backend pelo
**IP** (não `localhost`). O passo a passo completo, com os 4 ajustes alinhados ao
mesmo IP, está em [Acesso por outro dispositivo na rede](./08-acesso-rede-multidevice.md).

Resumo dos 4 ajustes (modo Backend Python):
1. Backend na rede: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
2. Frontend na rede: `npm run dev -- -H 0.0.0.0 -p 3000`
3. `frontend/.env`: `NEXT_PUBLIC_API_URL=http://<IP-da-maquina>:8000`
4. `backend/.env`: `FRONTEND_URL` e `BACKEND_PUBLIC_URL` com o mesmo IP (CORS + link do email)

## 5. Build de produção
```bash
npm run build && npm run start
```

> **Importante:** suba o backend **antes** do frontend, pois todas as tarefas são
> buscadas da API Python.
