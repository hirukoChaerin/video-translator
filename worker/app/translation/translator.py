"""Traducción de segmentos al idioma destino.

Importante: el modo `task="translate"` de Whisper SOLO traduce a inglés.
Para obtener español desde cualquier idioma, el flujo correcto es:
    transcribir en idioma original -> traducir texto -> español.

Estrategia de rutas de traducción (en orden de preferencia):
    1. Par directo:  ja -> es          (si existe el paquete)
    2. Pivote:       ja -> en -> es    (inglés como idioma puente)

El pivote cubre pares sin modelo directo (japonés, coreano, chino, etc.):
casi todos los idiomas tienen modelo hacia/desde inglés.

Patrones:
- Strategy (Protocol): `Translator` es la interfaz; se puede sustituir por
  DeepL/Google/NLLB implementando la misma interfaz.
- Null Object: PassthroughTranslator cuando el audio ya está en español.
- Chain: PivotTranslation compone dos traducciones como si fueran una.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Protocol

from app.transcription.engine import Segment, Transcript

logger = logging.getLogger(__name__)

PIVOT_LANGUAGE = "en"


class Translator(Protocol):
    def translate(self, transcript: Transcript, target: str) -> Transcript: ...


class PassthroughTranslator:
    """Null Object: no traduce (el contenido ya está en el idioma destino)."""

    def translate(self, transcript: Transcript, target: str) -> Transcript:
        return transcript


class _PivotTranslation:
    """Compone dos traducciones (src->en, en->dst) tras una misma interfaz.

    Para el pipeline es indistinguible de una traducción directa: recibe
    texto y devuelve texto. El costo es traducir dos veces, pero ocurre en
    CPU y es despreciable frente a la transcripción.
    """

    def __init__(self, first, second) -> None:
        self._first = first
        self._second = second

    def translate(self, text: str) -> str:
        return self._second.translate(self._first.translate(text))


class ArgosTranslator:
    """Traducción offline con Argos Translate (modelos OPUS-MT).

    Descarga e instala los paquetes de idioma la primera vez que se
    necesitan y los cachea en disco: los jobs siguientes no descargan nada.
    """

    def translate(self, transcript: Transcript, target: str) -> Transcript:
        source = transcript.language
        if source == target:
            return transcript

        translation = self._resolve_route(source, target)

        translated = tuple(
            Segment(start=s.start, end=s.end, text=translation.translate(s.text))
            for s in transcript.segments
        )
        return Transcript(language=target, segments=translated)

    # ---------- resolución de rutas ----------

    def _resolve_route(self, source: str, target: str):
        """Devuelve un objeto con .translate(str) -> str.

        Intenta el par directo; si no existe, pivota por inglés.
        """
        direct = self._try_get_translation(source, target)
        if direct is not None:
            logger.info("Ruta de traducción directa: %s -> %s", source, target)
            return direct

        logger.info(
            "Sin modelo directo %s -> %s; pivotando por '%s'",
            source, target, PIVOT_LANGUAGE,
        )
        to_pivot = self._try_get_translation(source, PIVOT_LANGUAGE)
        from_pivot = self._try_get_translation(PIVOT_LANGUAGE, target)

        match (to_pivot, from_pivot):
            case (None, _):
                raise RuntimeError(
                    f"No hay modelo de traducción {source} -> {PIVOT_LANGUAGE}"
                )
            case (_, None):
                raise RuntimeError(
                    f"No hay modelo de traducción {PIVOT_LANGUAGE} -> {target}"
                )
            case (first, second):
                return _PivotTranslation(first, second)

    def _try_get_translation(self, source: str, target: str):
        """Traducción instalada para el par, instalando el paquete si hace
        falta. Devuelve None si el par no existe en el índice de Argos."""
        import argostranslate.package as pkg
        import argostranslate.translate as tr

        translation = self._installed_pair(tr, source, target)
        if translation is not None:
            return translation

        # No instalado: buscar en el índice remoto
        pkg.update_package_index()
        candidates = [
            p for p in pkg.get_available_packages()
            if p.from_code == source and p.to_code == target
        ]
        if not candidates:
            return None

        logger.info("Instalando paquete de traducción %s -> %s", source, target)
        pkg.install_from_path(Path(candidates[0].download()))
        return self._installed_pair(tr, source, target)

    @staticmethod
    def _installed_pair(tr, source: str, target: str):
        installed = tr.get_installed_languages()
        src = next((l for l in installed if l.code == source), None)
        dst = next((l for l in installed if l.code == target), None)
        if src is None or dst is None:
            return None
        return src.get_translation(dst)


def pick_translator(detected_language: str, target: str) -> Translator:
    """Factory: elige la estrategia según el idioma detectado."""
    if detected_language == target:
        return PassthroughTranslator()
    return ArgosTranslator()
