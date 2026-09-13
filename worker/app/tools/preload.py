"""Precarga de modelos (Whisper + paquetes de traducción de Argos).

Descargar los modelos en un paso controlado —y no en mitad del primer job—
tiene dos ventajas:
  1. El primer video del usuario no tarda minutos extra ni falla por red.
  2. Los errores de red/TLS aparecen aquí, con un mensaje claro, y no como
     un job fallido en la cola.

Uso (una sola vez, o tras cambiar de modelo):
    docker compose run --rm worker python -m app.tools.preload
    # o con idiomas extra:
    docker compose run --rm worker python -m app.tools.preload ja ko zh
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from app.config import settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("preload")

# Idiomas de origen que se precargan por defecto (hacia inglés como pivote)
DEFAULT_SOURCES = ("en", "ja")
PIVOT = "en"


def preload_whisper() -> None:
    from faster_whisper import WhisperModel

    logger.info("Descargando modelo Whisper '%s'...", settings.whisper_model)
    # Instanciar el modelo dispara la descarga y lo deja en ~/.cache
    WhisperModel(settings.whisper_model, device="cpu", compute_type="int8")
    logger.info("Whisper listo.")


def preload_argos(sources: tuple[str, ...]) -> None:
    import argostranslate.package as pkg

    logger.info("Actualizando índice de paquetes de Argos...")
    pkg.update_package_index()
    available = pkg.get_available_packages()

    pairs: set[tuple[str, str]] = {(PIVOT, settings.target_language)}
    for src in sources:
        if src == settings.target_language:
            continue
        # par directo si existe; si no, el par hacia el pivote
        if any(p.from_code == src and p.to_code == settings.target_language for p in available):
            pairs.add((src, settings.target_language))
        else:
            pairs.add((src, PIVOT))

    for from_code, to_code in sorted(pairs):
        match [p for p in available if p.from_code == from_code and p.to_code == to_code]:
            case [package, *_]:
                logger.info("Instalando %s -> %s ...", from_code, to_code)
                pkg.install_from_path(Path(package.download()))
            case []:
                logger.warning("No existe paquete %s -> %s (se omite)", from_code, to_code)

    logger.info("Paquetes de traducción listos.")


def main() -> None:
    extra = tuple(sys.argv[1:])
    sources = tuple(dict.fromkeys(DEFAULT_SOURCES + extra))  # únicos, en orden
    preload_whisper()
    preload_argos(sources)
    logger.info("Precarga completa. Los jobs ya no necesitan descargar nada.")


if __name__ == "__main__":
    main()
