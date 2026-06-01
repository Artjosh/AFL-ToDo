# Acessar de outro dispositivo na rede (multi-device)

[← Voltar ao índice](../README.md)

Por padrão o frontend (`next dev`) e o backend (`uvicorn`) escutam só em
`localhost`, que **outros dispositivos não alcançam**. Para abrir o app no celular
(ou outro PC) na mesma rede Wi-Fi, é preciso fazê-los escutar na rede e apontar as
URLs para o **IP da sua máquina** (não `localhost`).

> Exemplos abaixo usam o IP `192.168.100.163`. Troque pelo IP da sua máquina:
> Windows `ipconfig` (procure "IPv4"), Linux/macOS `ip addr` / `ifconfig`.

## Diferença entre os modos (importante)

- **Backend Python (recomendado para multi-device local):** o link do email é
  gerado pelo **próprio backend** e o device de origem faz polling no backend. Se
  tudo apontar para o IP da máquina, funciona **100% na rede local**, sem nada
  externo.
- **Python + Supabase Auth:** o link é gerado pela **Supabase (nuvem)** e
  redireciona para o `emailRedirectTo`. Em rede local isso é problemático porque o
  IP `192.168.x.x` não é roteável de fora e muda por máquina. Para multi-device
  real no modo Supabase, use uma **URL pública** (deploy ou túnel `ngrok`/
  `cloudflared`) — ver [Configurar a Supabase](./04-configurar-supabase.md).

## Passo a passo (modo Backend Python)

São 4 ajustes alinhados ao mesmo IP:

### 1. Backend escutando na rede
```bash
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 2. Backend: `.env`
```env
# CORS: autoriza o frontend acessado pelo IP
FRONTEND_URL=http://192.168.100.163:3000
# Garante que o link do email use o IP (em vez de localhost)
BACKEND_PUBLIC_URL=http://192.168.100.163:8000
```

### 3. Frontend escutando na rede
```bash
cd frontend
npm run dev -- -H 0.0.0.0 -p 3000
```
A flag `-H 0.0.0.0` faz o Next escutar em todas as interfaces (sem ela, outros
devices não conectam). O Next também imprime o endereço de rede ao subir
(`Network: http://192.168.x.x:3000`).

### 4. Frontend: `.env.local`
```env
# O navegador do outro device precisa falar com o backend pelo IP, não localhost
NEXT_PUBLIC_API_URL=http://192.168.100.163:8000
```

### Pronto
No outro dispositivo, acesse `http://192.168.100.163:3000`. Peça o link no PC,
clique no celular (ou vice-versa) — a aba de origem detecta a confirmação por
polling.

## Dicas / problemas comuns

- **CORS bloqueado:** o `FRONTEND_URL` do backend precisa bater exatamente com a
  origem usada no navegador (mesmo IP e porta). Sem isso, a página abre mas as
  chamadas de API falham.
- **Firewall do Windows:** na primeira vez, o Windows pode pedir para liberar o
  Python/Node na rede privada — autorize.
- **Modo dev sem SMTP:** o link e o código aparecem na própria tela, então dá para
  testar o cross-device mesmo sem email configurado.
- **Produção:** use domínios reais em `FRONTEND_URL`, `BACKEND_PUBLIC_URL` e
  `NEXT_PUBLIC_API_URL`, atrás de HTTPS (ver [Produção](./15-producao.md)).
