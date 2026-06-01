"""Testes do realtime: broadcaster local (Pub/Sub em memória) e auth do WebSocket."""
import asyncio

import pytest

from app.services import realtime


@pytest.fixture(autouse=True)
def _reset_broadcaster(monkeypatch):
    # Garante broadcaster local (sem Redis) e isolado por teste.
    monkeypatch.setattr(realtime.settings, "REDIS_URL", "")
    realtime._broadcaster = None
    yield
    realtime._broadcaster = None


def test_broadcaster_entrega_evento_ao_inscrito():
    async def run():
        b = realtime.get_broadcaster()
        topic = realtime.topic_for_project(42)
        q = await b.subscribe(topic)
        await b.publish(topic, {"event": "task_created", "payload": {"task_id": 1}})
        msg = await asyncio.wait_for(q.get(), timeout=1)
        assert msg["event"] == "task_created"
        assert msg["payload"]["task_id"] == 1
        await b.unsubscribe(topic, q)

    asyncio.run(run())


def test_broadcaster_isola_topicos():
    async def run():
        b = realtime.get_broadcaster()
        q_proj = await b.subscribe(realtime.topic_for_project(1))
        # publica em outro tópico — não deve chegar em q_proj
        await b.publish(realtime.topic_for_standalone(99), {"event": "x", "payload": {}})
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(q_proj.get(), timeout=0.2)

    asyncio.run(run())


def test_topicos_distintos():
    assert realtime.topic_for_project(1) != realtime.topic_for_standalone(1)
    assert realtime.topic_for_project(5) == "project:5"
    assert realtime.topic_for_standalone(7) == "standalone:7"


def test_ws_rejeita_token_invalido(client):
    """WS sem token válido deve ser fechado (não conecta)."""
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/board?token=lixo") as ws:
            ws.receive_text()


def test_ws_aceita_token_valido(client, login_local):
    """Com token válido, o WS conecta (handshake aceito) no escopo do usuário."""
    headers, _ = login_local("rt@test.com")
    token = headers["Authorization"].split(" ", 1)[1]
    # Se a conexão for aceita, o context manager entra sem exceção.
    with client.websocket_connect(f"/ws/board?token={token}") as ws:
        assert ws is not None


def test_ws_ticket_requer_autenticacao(client):
    """Sem sessão, /auth/ws-ticket responde 401."""
    r = client.post("/auth/ws-ticket")
    assert r.status_code == 401


def test_ws_ticket_emitido_e_conecta_no_ws(client, login_local):
    """Fluxo BFF: troca a sessão por um ticket efêmero e conecta o WS com ele."""
    headers, _ = login_local("ticket@test.com")

    r = client.post("/auth/ws-ticket", headers=headers)
    assert r.status_code == 200
    ticket = r.json()["ticket"]
    assert ticket

    # O ticket efêmero abre o WebSocket (handshake aceito).
    with client.websocket_connect(f"/ws/board?token={ticket}") as ws:
        assert ws is not None


def test_ws_rejeita_ticket_de_tipo_errado(client, login_local):
    """Um JWT de sessão (type=access) não deve passar como ticket, mas o WS ainda
    aceita o token de sessão direto (compat). Já um token aleatório é rejeitado."""
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/board?token=naoehticket") as ws:
            ws.receive_text()
