"""Punto de entrada del worker: consume la cola BullMQ desde Python.

El paquete `bullmq` (cliente oficial) habla el mismo protocolo Redis que el
api-gateway en Node, por lo que ambos lenguajes comparten la misma cola sin
puentes intermedios.

Composición (Composition Root): aquí —y solo aquí— se construyen las
implementaciones concretas y se inyectan en el pipeline.
"""

from __future__ import annotations

import asyncio
import logging
import signal
from pathlib import Path

from bullmq import Worker

from app import notifier
from app.config import settings
from app.pipeline import JobInput, TranslationPipeline
from app.transcription.engine import FasterWhisperEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("worker")

# El motor se crea UNA vez por proceso: el modelo Whisper se comparte entre
# jobs (cargarlo en cada job duplicaría tiempo y RAM sin beneficio alguno).
pipeline = TranslationPipeline(
    engine=FasterWhisperEngine(
        model_name=settings.whisper_model,
        device=settings.whisper_device,
        compute_type=settings.whisper_compute_type,
    )
)


async def process(job, _token: str) -> dict:
    """Handler de BullMQ. Lo que retorna se guarda como `returnvalue` del job
    y llega al frontend a través del api-gateway."""
    data = job.data
    logger.info("Job %s recibido: %s", job.id, data.get("originalName"))

    job_input = JobInput(
        job_id=str(data["jobId"]),
        input_path=Path(data["inputPath"]),
        output_dir=Path(data["outputDir"]),
        original_name=str(data.get("originalName", "video")),
    )

    async def report(progress: int) -> None:
        await job.updateProgress(progress)

    try:
        result = await pipeline.run(job_input, report)
    except Exception as exc:
        # Notificamos el fallo y relanzamos: BullMQ aplicará los reintentos
        # con backoff configurados por el api-gateway.
        await notifier.notify_finished(
            job_input.job_id, {"status": "failed", "error": str(exc)}
        )
        raise

    payload = result.as_dict()
    await notifier.notify_finished(job_input.job_id, {"status": "completed", **payload})
    logger.info("Job %s completado: %s", job.id, payload["artifacts"])
    return payload


async def main() -> None:
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)

    worker = Worker(
        settings.queue_name,
        process,
        {
            "connection": settings.redis_url,
            "concurrency": settings.concurrency,
            # El lock se RENUEVA solo cada lockDuration/2 mientras el job
            # viva (el pipeline usa asyncio.to_thread, así que el event loop
            # queda libre para renovarlo). 2 min da margen ante picos de CPU
            # y, si el worker muere, el job se reintenta en ~2 min en vez de
            # quedar bloqueado horas. NO lo subas al tamaño del video.
            "lockDuration": 2 * 60 * 1000,
        },
    )

    logger.info(
        "Worker escuchando cola '%s' (modelo=%s, device=%s, concurrencia=%d)",
        settings.queue_name, settings.whisper_model,
        settings.whisper_device, settings.concurrency,
    )

    await stop.wait()  # bloquea hasta SIGTERM/SIGINT

    logger.info("Cerrando worker (esperando jobs activos)...")
    await worker.close()      # espera a que terminen los jobs en curso
    await notifier.close()
    logger.info("Worker detenido limpiamente")


if __name__ == "__main__":
    asyncio.run(main())
