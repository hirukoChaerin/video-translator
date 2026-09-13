"""Notificación HTTP al api-gateway cuando un job termina.

httpx.AsyncClient reutilizable (pool de conexiones) en lugar de crear un
cliente por request. El fallo del callback NO tumba el job: BullMQ ya
propaga el resultado por Redis; el webhook es un canal complementario.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_client = httpx.AsyncClient(
    base_url=settings.api_base_url,
    headers={"x-internal-token": settings.internal_token},
    timeout=10.0,
)


async def notify_finished(job_id: str, payload: dict[str, Any]) -> None:
    try:
        response = await _client.post(f"/internal/jobs/{job_id}/finished", json=payload)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("Callback al api-gateway falló (no crítico): %s", exc)


async def close() -> None:
    await _client.aclose()
