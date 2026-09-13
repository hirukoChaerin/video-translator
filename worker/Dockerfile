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
# Si la carpeta solo tiene .gitkeep, este paso no hace nada.
# ---------------------------------------------------------------
COPY certs/ /usr/local/share/ca-certificates/extra/
RUN update-ca-certificates

# Que TODO el ecosistema Python (requests, httpx, huggingface_hub, pip)
# use el bundle del sistema, que ya incluye la CA corporativa:
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    PIP_CERT=/etc/ssl/certs/ca-certificates.crt

WORKDIR /srv/worker

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# PYTHONUNBUFFERED: logs en tiempo real en `docker logs`
ENV PYTHONUNBUFFERED=1
CMD ["python", "-m", "app.main"]
