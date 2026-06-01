"""Realtime do board via WebSocket, com fan-out por Redis Pub/Sub.

Quando uma tarefa/projeto muda, o backend publica um evento num "tópico" (por
projeto, ou "standalone:<user_id>" para tarefas soltas). Os clientes conectados
via WebSocket naquele tópico recebem o evento e atualizam o board ao vivo.

- Com Redis: usa Pub/Sub, então o fan-out funciona entre VÁRIOS processos/réplicas
  do backend (um cliente conectado na réplica A recebe evento publicado na B).
- Sem Redis: usa um broadcaster em memória (funciona só dentro do mesmo processo),
  suficiente para dev/single-instance.
"""
from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from typing import Any

from app.core.config import settings


class _LocalBroadcaster:
    """Fan-out em memória (single-process). Fallback sem Redis."""

    def __init__(self) -> None:
        self._subs: dict[str, set[asyncio.Queue]] = defaultdict(set)

    async def publish(self, topic: str, message: dict[str, Any]) -> None:
        for q in list(self._subs.get(topic, ())):
            q.put_nowait(message)

    async def subscribe(self, topic: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subs[topic].add(q)
        return q

    async def unsubscribe(self, topic: str, q: asyncio.Queue) -> None:
        self._subs[topic].discard(q)


class _RedisBroadcaster:
    """Fan-out via Redis Pub/Sub (multi-process)."""

    CHANNEL_PREFIX = "rt:"

    def __init__(self, url: str) -> None:
        self._url = url
        self._redis = None

    async def _client(self):
        if self._redis is None:
            import redis.asyncio as aioredis

            self._redis = aioredis.from_url(self._url, decode_responses=True)
        return self._redis

    async def publish(self, topic: str, message: dict[str, Any]) -> None:
        client = await self._client()
        await client.publish(self.CHANNEL_PREFIX + topic, json.dumps(message))

    async def subscribe(self, topic: str):
        import redis.asyncio as aioredis

        client = aioredis.from_url(self._url, decode_responses=True)
        pubsub = client.pubsub()
        await pubsub.subscribe(self.CHANNEL_PREFIX + topic)
        return pubsub

    async def unsubscribe(self, topic: str, pubsub) -> None:
        try:
            await pubsub.unsubscribe(self.CHANNEL_PREFIX + topic)
            await pubsub.aclose()
        except Exception:
            pass


_broadcaster: _LocalBroadcaster | _RedisBroadcaster | None = None
# Loop principal do servidor (capturado no startup) — permite publicar a partir
# das rotas sync, que rodam num threadpool fora do event loop.
_main_loop: asyncio.AbstractEventLoop | None = None


def set_main_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _main_loop
    _main_loop = loop


def get_broadcaster() -> _LocalBroadcaster | _RedisBroadcaster:
    global _broadcaster
    if _broadcaster is None:
        if settings.redis_enabled:
            _broadcaster = _RedisBroadcaster(settings.REDIS_URL)
        else:
            _broadcaster = _LocalBroadcaster()
    return _broadcaster


def topic_for_project(project_id: int) -> str:
    return f"project:{project_id}"


def topic_for_standalone(user_id: int) -> str:
    return f"standalone:{user_id}"


async def publish_board_event(topic: str, event: str, payload: dict[str, Any]) -> None:
    """Publica um evento de board no tópico. Tolerante a falhas (não derruba a request)."""
    try:
        await get_broadcaster().publish(topic, {"event": event, "payload": payload})
    except Exception:
        pass


def notify_board(topic: str, event: str, payload: dict[str, Any]) -> None:
    """Versão síncrona (fire-and-forget) para chamar de rotas sync.

    As rotas sync do FastAPI rodam num threadpool (fora do event loop). Por isso
    publicamos no loop principal do servidor via run_coroutine_threadsafe, quando
    ele foi capturado no startup. Fallbacks cobrem o caso de já estar no loop
    (rota async) e o caso de não haver loop (testes). Nunca propaga exceção.
    """
    coro_factory = lambda: publish_board_event(topic, event, payload)  # noqa: E731

    # 1) Já dentro de um event loop (ex.: chamada async): agenda nele.
    try:
        running = asyncio.get_running_loop()
    except RuntimeError:
        running = None
    if running is not None:
        running.create_task(coro_factory())
        return

    # 2) Rota sync no threadpool: publica no loop principal do servidor.
    if _main_loop is not None and _main_loop.is_running():
        try:
            asyncio.run_coroutine_threadsafe(coro_factory(), _main_loop)
            return
        except Exception:
            pass

    # 3) Sem loop (ex.: testes sync): executa de forma isolada, best-effort.
    coro = coro_factory()
    try:
        asyncio.run(coro)
    except Exception:
        coro.close()
