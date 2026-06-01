"""WebSocket de realtime do board.

O cliente conecta em /ws/board?token=<jwt>&project_id=<id|omitido>. O backend:
1. valida o token (mesma lógica do get_current_user, mas para WS);
2. valida o acesso ao escopo (projeto compartilhado ou tarefas soltas do usuário);
3. assina o tópico e repassa os eventos recebidos para o cliente.

Eventos são publicados pelas rotas de tarefas/projetos via publish_board_event.
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.api.access import get_accessible_project, task_is_accessible  # noqa: F401
from app.api.deps import _get_or_create_user_from_supabase, _get_user_from_local_token
from app.core.config import settings
from app.core.security import decode_ws_ticket
from app.db.session import SessionLocal
from app.models.user import User
from app.services.realtime import (
    get_broadcaster,
    topic_for_project,
    topic_for_standalone,
)

router = APIRouter(tags=["realtime"])


def _resolve_user(token: str, db: Session) -> User | None:
    """Resolve o usuário a partir do token do WS.

    Aceita, nesta ordem:
    1. Ticket efêmero de WS (type=ws) emitido por /auth/ws-ticket — padrão BFF.
    2. JWT de sessão local (type=access) — usado direto em testes/compat.
    3. Token da Supabase (quando o modo está habilitado).
    """
    ticket = decode_ws_ticket(token)
    if ticket is not None:
        sub = ticket.get("sub")
        try:
            user_id = int(sub)
        except (TypeError, ValueError):
            return None
        return db.query(User).filter(User.id == user_id).first()

    user = _get_user_from_local_token(token, db)
    if user is None and settings.supabase_enabled:
        user = _get_or_create_user_from_supabase(token, db)
    return user


def _resolve_topic(token: str, project_id: int | None) -> str | None:
    """Valida token + acesso ao escopo numa única sessão; retorna o tópico ou None."""
    db = SessionLocal()
    try:
        user = _resolve_user(token, db)
        if user is None:
            return None

        if project_id is not None:
            try:
                get_accessible_project(db, project_id, user)
            except Exception:
                return None
            return topic_for_project(project_id)
        return topic_for_standalone(user.id)
    finally:
        db.close()


@router.websocket("/ws/board")
async def ws_board(
    websocket: WebSocket,
    token: str = Query(...),
    project_id: int | None = Query(default=None),
) -> None:
    topic = _resolve_topic(token, project_id)
    if topic is None:
        await websocket.close(code=4401)  # sem auth/sem acesso
        return

    await websocket.accept()
    broadcaster = get_broadcaster()
    sub = await broadcaster.subscribe(topic)

    try:
        if hasattr(sub, "get"):  # _LocalBroadcaster: asyncio.Queue
            await _pump_local(websocket, sub)
        else:  # _RedisBroadcaster: pubsub
            await _pump_redis(websocket, sub)
    except WebSocketDisconnect:
        pass
    finally:
        await broadcaster.unsubscribe(topic, sub)


async def _pump_local(websocket: WebSocket, queue: asyncio.Queue) -> None:
    while True:
        message = await queue.get()
        await websocket.send_json(message)


async def _pump_redis(websocket: WebSocket, pubsub) -> None:
    import json

    while True:
        msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=30)
        if msg is None:
            # keep-alive: detecta desconexão
            await websocket.send_json({"event": "ping", "payload": {}})
            continue
        data = msg.get("data")
        if data:
            await websocket.send_json(json.loads(data))
