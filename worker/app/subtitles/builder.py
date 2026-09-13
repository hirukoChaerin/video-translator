"""Generación de archivos de subtítulos SRT y VTT.

Funciones puras: reciben datos y devuelven texto. Sin I/O ni estado global,
por lo que son triviales de testear.
"""

from __future__ import annotations

from app.transcription.engine import Transcript


def _timestamp(seconds: float, *, vtt: bool = False) -> str:
    ms = round(seconds * 1000)
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1_000)
    sep = "." if vtt else ","
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def to_srt(transcript: Transcript) -> str:
    blocks = (
        f"{i}\n{_timestamp(seg.start)} --> {_timestamp(seg.end)}\n{seg.text}\n"
        for i, seg in enumerate(transcript.segments, start=1)
    )
    return "\n".join(blocks)


def to_vtt(transcript: Transcript) -> str:
    blocks = (
        f"{_timestamp(seg.start, vtt=True)} --> {_timestamp(seg.end, vtt=True)}\n{seg.text}\n"
        for seg in transcript.segments
    )
    return "WEBVTT\n\n" + "\n".join(blocks)
