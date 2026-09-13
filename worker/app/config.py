"""Configuración centralizada del worker.

Buenas prácticas Python 3.12+:
- dataclass(frozen=True, slots=True): inmutable y con menor huella de RAM
  (slots evita el __dict__ por instancia).
- Un solo punto de lectura de os.environ, igual que en el api-gateway.
- Type hints completos: sirven de documentación y permiten mypy/pyright.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True, slots=True)
class Settings:
    redis_host: str = field(default_factory=lambda: _env("REDIS_HOST", "127.0.0.1"))
    redis_port: int = field(default_factory=lambda: int(_env("REDIS_PORT", "6379")))
    queue_name: str = field(default_factory=lambda: _env("QUEUE_NAME", "video-translation"))

    storage_root: Path = field(default_factory=lambda: Path(_env("STORAGE_ROOT", "./storage")))

    whisper_model: str = field(default_factory=lambda: _env("WHISPER_MODEL", "small"))
    whisper_device: str = field(default_factory=lambda: _env("WHISPER_DEVICE", "auto"))
    whisper_compute_type: str = field(default_factory=lambda: _env("WHISPER_COMPUTE_TYPE", "auto"))

    target_language: str = field(default_factory=lambda: _env("TARGET_LANGUAGE", "es"))
    burn_subtitles: bool = field(
        default_factory=lambda: _env("BURN_SUBTITLES", "true").lower() == "true"
    )
    video_encoder: str = field(default_factory=lambda: _env("VIDEO_ENCODER", "libx264"))
    concurrency: int = field(default_factory=lambda: int(_env("WORKER_CONCURRENCY", "1")))

    api_base_url: str = field(default_factory=lambda: _env("API_BASE_URL", "http://localhost:4000"))
    internal_token: str = field(default_factory=lambda: _env("INTERNAL_TOKEN", "dev-token"))

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}"


settings = Settings()
