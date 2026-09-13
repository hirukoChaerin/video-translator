"""Transcripción de audio.

Patrón Strategy con typing.Protocol: `Pipeline` depende de la interfaz
`TranscriptionEngine`, no de faster-whisper. Mañana se puede cambiar por la
API de OpenAI o por otro modelo sin tocar el resto del código.

faster-whisper (CTranslate2) vs openai-whisper:
- ~4x más rápido y ~2-3x menos RAM/VRAM con la misma precisión.
- Soporta int8 en CPU y float16 en GPU.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Protocol

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Segment:
    """Fragmento de habla con marcas de tiempo (unidad de trabajo del pipeline)."""

    start: float
    end: float
    text: str


@dataclass(frozen=True, slots=True)
class Transcript:
    language: str
    segments: tuple[Segment, ...]


class TranscriptionEngine(Protocol):
    def transcribe(self, audio: Path) -> Transcript: ...


class FasterWhisperEngine:
    """Implementación con faster-whisper y carga perezosa del modelo.

    Lazy loading: el modelo (cientos de MB) solo se carga en el primer job.
    Después se reutiliza entre jobs: cargarlo por trabajo sería el mayor
    desperdicio de RAM/tiempo del worker.
    """

    def __init__(self, model_name: str, device: str = "auto", compute_type: str = "auto") -> None:
        self._model_name = model_name
        self._device = device
        self._compute_type = compute_type
        self._model = None  # se crea bajo demanda

    def _load(self):
        if self._model is None:
            from faster_whisper import WhisperModel  # import diferido: arranque rápido

            logger.info(
                "Cargando modelo Whisper '%s' (device=%s, compute=%s)",
                self._model_name, self._device, self._compute_type,
            )
            self._model = WhisperModel(
                self._model_name,
                device=self._device,
                compute_type=self._compute_type,
            )
        return self._model

    def transcribe(self, audio: Path) -> Transcript:
        model = self._load()
        # vad_filter recorta silencios: menos alucinaciones y menos cómputo
        raw_segments, info = model.transcribe(str(audio), vad_filter=True)

        segments = tuple(
            Segment(start=s.start, end=s.end, text=s.text.strip())
            for s in self._non_empty(raw_segments)
        )
        logger.info("Transcritos %d segmentos (idioma=%s)", len(segments), info.language)
        return Transcript(language=info.language, segments=segments)

    @staticmethod
    def _non_empty(segments) -> Iterator:
        return (s for s in segments if s.text and s.text.strip())
