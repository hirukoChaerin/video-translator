"""Pipeline de traducción de video: la lógica de negocio del worker.

Patrón Pipeline / Template Method: el flujo (audio -> transcripción ->
traducción -> subtítulos -> render) está fijo aquí; cada etapa es una
dependencia inyectada e intercambiable.

Inyección de dependencias por constructor: `main.py` decide QUÉ motor de
transcripción usar; el pipeline solo sabe CÓMO encadenarlos. Esto permite
testear el pipeline con dobles (fakes) sin GPU ni modelos.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable

from app.config import settings
from app.media import ffmpeg
from app.subtitles.builder import to_srt, to_vtt
from app.transcription.engine import TranscriptionEngine
from app.translation.translator import pick_translator

logger = logging.getLogger(__name__)

ProgressFn = Callable[[int], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class JobInput:
    job_id: str
    input_path: Path
    output_dir: Path
    original_name: str


@dataclass(frozen=True, slots=True)
class JobResult:
    source_language: str
    segments: int
    artifacts: dict[str, str]  # rutas RELATIVAS a storage/outputs

    def as_dict(self) -> dict:
        return {
            "sourceLanguage": self.source_language,
            "segments": self.segments,
            "artifacts": self.artifacts,
        }


class TranslationPipeline:
    def __init__(self, engine: TranscriptionEngine) -> None:
        self._engine = engine

    async def run(self, job: JobInput, report: ProgressFn) -> JobResult:
        job.output_dir.mkdir(parents=True, exist_ok=True)
        workdir = job.output_dir / "tmp"
        workdir.mkdir(exist_ok=True)

        try:
            # Las etapas pesadas (ffmpeg, Whisper, traducción) son código
            # SÍNCRONO y bloqueante. Se ejecutan en un hilo con
            # asyncio.to_thread para que el event loop quede libre: BullMQ
            # necesita el loop para renovar el lock del job cada
            # lockDuration/2. Sin esto, un video largo congela el loop,
            # el lock expira y el job se marca como "stalled" a mitad.

            # 1) Audio (10 %)
            audio = await asyncio.to_thread(
                ffmpeg.extract_audio, job.input_path, workdir / "audio.wav"
            )
            await report(10)

            # 2) Transcripción, la etapa más costosa (10 % -> 60 %)
            transcript = await asyncio.to_thread(self._engine.transcribe, audio)
            await report(60)

            # 3) Traducción al idioma destino (60 % -> 75 %)
            translator = pick_translator(transcript.language, settings.target_language)
            translated = await asyncio.to_thread(
                translator.translate, transcript, settings.target_language
            )
            await report(75)

            # 4) Subtítulos SRT + VTT (75 % -> 80 %)
            srt_path = job.output_dir / "subtitulos.es.srt"
            vtt_path = job.output_dir / "subtitulos.es.vtt"
            srt_path.write_text(to_srt(translated), encoding="utf-8")
            vtt_path.write_text(to_vtt(translated), encoding="utf-8")
            await report(80)

            artifacts = {
                "srt": f"{job.job_id}/{srt_path.name}",
                "vtt": f"{job.job_id}/{vtt_path.name}",
            }

            # 5) Video con subtítulos incrustados, opcional (80 % -> 100 %)
            if settings.burn_subtitles:
                out_video = job.output_dir / f"traducido_{Path(job.original_name).stem}.mp4"
                await asyncio.to_thread(
                    ffmpeg.burn_subtitles, job.input_path, srt_path, out_video
                )
                artifacts["video"] = f"{job.job_id}/{out_video.name}"

            await report(100)
            return JobResult(
                source_language=transcript.language,
                segments=len(translated.segments),
                artifacts=artifacts,
            )
        finally:
            # Los intermedios (WAV puede pesar cientos de MB) se borran SIEMPRE,
            # incluso si el job falla: el disco también es un recurso a cuidar.
            shutil.rmtree(workdir, ignore_errors=True)
