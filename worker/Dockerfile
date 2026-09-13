# syntax=docker/dockerfile:1
ARG PY_VERSION=3.14
FROM python:${PY_VERSION}-slim

# ffmpeg + ca-certificates (necesario para descargar modelos por HTTPS)
RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------
# CA corporativa (redes con inspección SSL: Zscaler, Fortinet...)
# Coloca el .crt en worker/certs/ y se instala automáticamente.
# ---------------------------------------------------------------
COPY certs/ /usr/local/share/ca-certificates/extra/
RUN update-ca-certificates

ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    PIP_CERT=/etc/ssl/certs/ca-certificates.crt

WORKDIR /srv/worker

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---------------------------------------------------------------
# Soporte GPU (opcional): --build-arg GPU=true
# CTranslate2 (faster-whisper) necesita cuBLAS y cuDNN 9 para CUDA 12.
# Se instalan como wheels de pip (no hace falta el CUDA Toolkit completo,
# que pesaría varios GB) y se registran en el linker del sistema.
# El driver NVIDIA NO va en la imagen: lo inyecta nvidia-container-toolkit.
# ---------------------------------------------------------------
ARG GPU=false
RUN if [ "$GPU" = "true" ]; then \
      pip install --no-cache-dir nvidia-cublas-cu12 "nvidia-cudnn-cu12==9.*" && \
      python -c "import pathlib, site; libs = [str(p) for sp in site.getsitepackages() for p in pathlib.Path(sp).glob('nvidia/*/lib')]; pathlib.Path('/etc/ld.so.conf.d/nvidia-pip.conf').write_text('\n'.join(libs) + '\n')" && \
      ldconfig; \
    fi

COPY app ./app

# PYTHONUNBUFFERED: logs en tiempo real en `docker logs`
ENV PYTHONUNBUFFERED=1
CMD ["python", "-m", "app.main"]
