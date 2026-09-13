"""Operaciones de FFmpeg vía subprocess.

Por qué subprocess y no un binding de Python: FFmpeg hace streaming en C con
RAM constante; el proceso Python solo orquesta. Nunca cargamos el video en
memoria.

Seguridad: siempre lista de argumentos (nunca shell=True) para evitar
inyección de comandos con nombres de archivo maliciosos.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


class FFmpegError(RuntimeError):
    """El proceso ffmpeg terminó con código distinto de cero."""


class NoAudioStreamError(RuntimeError):
    """El archivo no contiene ninguna pista de audio: no hay nada que
    transcribir. Error de dominio con mensaje apto para el usuario final."""

    def __init__(self) -> None:
        super().__init__(
            "El video no tiene pista de audio, así que no hay nada que "
            "transcribir. Suele pasar con descargas de Google/YouTube donde "
            "el audio viene en un archivo separado. Verifica el archivo con: "
            "ffprobe -show_entries stream=codec_type tu_video.mp4"
        )


def _run(args: list[str]) -> subprocess.CompletedProcess:
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        # Solo las últimas líneas de stderr: suficiente para diagnosticar
        tail = "\n".join(result.stderr.strip().splitlines()[-8:])
        raise FFmpegError(f"ffmpeg falló ({result.returncode}):\n{tail}")
    return result


def has_audio_stream(video: Path) -> bool:
    """Comprueba con ffprobe si el archivo tiene al menos una pista de audio.

    Validar ANTES de procesar (fail fast) convierte un volcado críptico de
    ffmpeg en un error de dominio claro para el usuario.
    """
    result = _run([
        "ffprobe", "-v", "error",
        "-select_streams", "a",
        "-show_entries", "stream=index",
        "-of", "csv=p=0",
        str(video),
    ])
    return bool(result.stdout.strip())


def extract_audio(video: Path, out_wav: Path) -> Path:
    """Extrae el audio en WAV 16 kHz mono, el formato nativo de Whisper.

    Convertir aquí (y no dejar que Whisper decodifique el video) reduce el
    trabajo del modelo y el tamaño del archivo intermedio.
    """
    if not has_audio_stream(video):
        raise NoAudioStreamError()

    out_wav.parent.mkdir(parents=True, exist_ok=True)
    _run([
        "ffmpeg", "-y",
        "-i", str(video),
        "-vn",                # sin video
        "-ac", "1",           # mono
        "-ar", "16000",       # 16 kHz
        "-c:a", "pcm_s16le",
        str(out_wav),
    ])
    return out_wav


def burn_subtitles(video: Path, srt: Path, out_video: Path) -> Path:
    """Incrusta los subtítulos en el video (hardsub).

    - El audio se copia sin recodificar (-c:a copy): más rápido y sin pérdida.
    - preset veryfast + crf 23: buen equilibrio calidad/CPU para un MVP.
    """
    out_video.parent.mkdir(parents=True, exist_ok=True)
    # El filtro subtitles necesita escapar caracteres especiales de la ruta
    srt_arg = str(srt).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    _run([
        "ffmpeg", "-y",
        "-i", str(video),
        "-vf", f"subtitles='{srt_arg}'",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-c:a", "copy",
        str(out_video),
    ])
    return out_video
