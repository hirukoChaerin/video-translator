# Subtitulador — Traducción de videos al español

Aplicación de microservicios que recibe un video en cualquier idioma, lo transcribe con Whisper, traduce el texto al español y devuelve subtítulos `.srt`/`.vtt` y, opcionalmente, el video con los subtítulos incrustados.

## Arquitectura

```
┌────────────┐  HTTP (multipart) ┌──────────────────┐   add job    ┌─────────┐
│  Frontend  │ ────────────────▶ │   API Gateway     │ ───────────▶ │  Redis  │
│  React 19  │ ◀──────────────── │ Node 24 + Express │ ◀─────────── │ BullMQ  │
│   (Vite)   │   SSE (progreso)  │         5         │  QueueEvents └────┬────┘
└────────────┘                   └────────┬─────────┘                    │ consume
                                          │ webhook /internal            ▼
                                          │                    ┌──────────────────┐
                                 ┌────────┴────────┐           │  Worker Python   │
                                 │ storage/ (disco │ ◀───────▶ │ 3.14: FFmpeg +   │
                                 │ compartido)     │           │ Whisper + Argos  │
                                 └─────────────────┘           └──────────────────┘
```

Flujo: `subir video → job en cola → extraer audio (FFmpeg) → transcribir (faster-whisper, GPU si hay) → traducir a es (Argos) → generar SRT/VTT → incrustar subtítulos → notificar`.

El progreso llega al navegador por **Server-Sent Events**: el worker hace `job.updateProgress(n)`, BullMQ lo publica en Redis, `QueueEvents` lo captura en Node y el gateway lo reenvía a la conexión SSE abierta.

## Ejecutar

```bash
cp .env.example .env      # ajusta INTERNAL_TOKEN
docker compose up --build
# Frontend:  http://localhost:5173
# API:       http://localhost:4000/health
```

Con GPU NVIDIA: instala `nvidia-container-toolkit`, descomenta el bloque `deploy` del worker en `docker-compose.yml` y usa `WHISPER_DEVICE=cuda` + `WHISPER_COMPUTE_TYPE=float16`.

Desarrollo local sin Docker:

```bash
# Terminal 1: redis
docker run -p 6379:6379 redis:7.4-alpine
# Terminal 2: api (Node 24 lee .env de forma nativa, sin dotenv)
cd api-gateway && npm i && npm run dev
# Terminal 3: worker
cd worker && pip install -r requirements.txt && STORAGE_ROOT=../storage python -m app.main
# Terminal 4: frontend
cd frontend && npm i && npm run dev
```

## Decisiones de buenas prácticas

### Node 24 + Express 5 (api-gateway)
- **ESM nativo** (`"type": "module"`), `crypto.randomUUID()` y prefijo `node:` en imports internos — cero dependencias para lo que la plataforma ya trae.
- **Express 5 propaga errores async** al middleware de error automáticamente: no hay `try/catch` repetido ni wrappers `catchAsync`.
- **Capas separadas**: `routes` (HTTP) → `services` (negocio) → `queues` (infra). Los servicios no conocen `req/res`, así que se testean sin levantar el servidor.
- **RAM constante en subidas y descargas**: multer con `diskStorage` (streaming al disco) y `res.download` (streaming desde disco). Un video de 1 GB nunca pasa por la memoria del proceso.
- **Graceful shutdown**: al recibir `SIGTERM` se cierra el servidor HTTP y luego la cola, dentro de la ventana que da Docker/Kubernetes antes del `SIGKILL`.
- **Higiene de Redis**: `removeOnComplete/removeOnFail` con límites — Redis vive en RAM y no debe acumular historial infinito.
- `node --watch` y `--env-file` nativos en desarrollo (sin nodemon ni dotenv).

### React 19 + Vite (frontend)
- **`useActionState`** gestiona la acción de subida (pending + error + reset) sin el trío clásico de `useState`.
- **`useFormStatus`** en el botón de envío: conoce el `pending` del formulario sin prop drilling.
- **Hook personalizado `useJobProgress`**: encapsula el ciclo de vida completo del `EventSource`, con limpieza en el `return` del efecto (sin conexiones zombie).
- Componentes de presentación puros (`JobCard`) separados de la lógica de datos.
- Build multi-stage: la imagen final es nginx con estáticos (~50 MB), sin Node en producción.

### Python 3.14 (worker)
- **`dataclass(frozen=True, slots=True)`** para configuración y modelos: inmutables y con menor huella de memoria.
- **Strategy con `typing.Protocol`**: `TranscriptionEngine` y `Translator` son interfaces; cambiar faster-whisper por la API de OpenAI, o Argos por DeepL, no toca el pipeline.
- **Null Object** (`PassthroughTranslator`) cuando el audio ya está en español.
- **Composition root** en `main.py`: las implementaciones concretas se construyen una sola vez y se inyectan.
- **El modelo Whisper se carga una vez por proceso** (lazy) y se reutiliza entre jobs — recargar cientos de MB por trabajo sería el mayor desperdicio posible.
- `structural pattern matching` (`match/case`) en la instalación de paquetes de traducción; `pathlib` en todo el I/O; type hints completos.
- Los temporales (el WAV puede pesar cientos de MB) se borran en `finally`, incluso si el job falla.

### Patrones de diseño usados
| Patrón | Dónde | Para qué |
|---|---|---|
| Singleton (por módulo) | `video.queue.js`, motor Whisper | Una conexión/modelo por proceso |
| Service Layer | `job.service.js` | Negocio separado de HTTP |
| Observer | `QueueEvents` → SSE | Progreso en vivo desacoplado del worker |
| Strategy | `TranscriptionEngine`, `Translator` | Motores intercambiables |
| Null Object | `PassthroughTranslator` | Sin `if` de idioma en el pipeline |
| Factory | `pick_translator` | Elegir la estrategia según el idioma |
| Pipeline | `TranslationPipeline` | Etapas ordenadas con progreso |

## Notas técnicas importantes

- **Whisper solo "traduce" a inglés** con `task=translate`. Para español el flujo correcto es transcribir en el idioma original y traducir el texto después (aquí, con Argos Translate en local, sin APIs de pago).
- **faster-whisper** (CTranslate2) en lugar de `openai-whisper`: ~4x más rápido y 2–3x menos RAM/VRAM con la misma precisión.
- **Python 3.14**: si alguna librería de ML aún no publica wheels para 3.14, baja la versión con `docker compose build --build-arg PY_VERSION=3.12 worker` sin tocar el código.
- **Escalar**: el worker es el cuello de botella natural; `docker compose up --scale worker=3` levanta más consumidores de la misma cola sin cambiar nada más. En Kubernetes, cada servicio es un Deployment independiente.
- **Almacenamiento**: hoy es disco compartido (`./storage`). Para migrar a S3/MinIO solo hay que tocar `storage.service`/rutas de descarga en el gateway y las rutas de salida del pipeline — el resto no cambia.
- **Seguridad**: nombres de archivo regenerados (UUID), validación de MIME, protección contra path traversal en descargas, token con `timingSafeEqual` en el canal interno, `helmet` y usuario sin privilegios en los contenedores.

## Solución de problemas

### `CERTIFICATE_VERIFY_FAILED: self-signed certificate in certificate chain`

Tu red (proxy/firewall corporativo o antivirus) intercepta el HTTPS y firma con su propia CA, que el contenedor no conoce. Solución:

1. Consigue el certificado raíz de tu red en formato PEM (pídelo a TI, o expórtalo desde el navegador: candado → certificado → cadena → raíz → exportar como Base-64 `.crt`).
2. Cópialo a `worker/certs/mi-red.crt` (la extensión debe ser `.crt`).
3. Reconstruye: `docker compose build worker`.

El Dockerfile lo instala con `update-ca-certificates` y exporta `SSL_CERT_FILE`/`REQUESTS_CA_BUNDLE`, de modo que requests, httpx, huggingface_hub y pip confían en él. **Nunca** desactives la verificación SSL como atajo.

### Precargar modelos (recomendado)

Descarga Whisper y los paquetes de traducción una sola vez, fuera del flujo de jobs:

```bash
docker compose run --rm worker python -m app.tools.preload        # en + ja -> es
docker compose run --rm worker python -m app.tools.preload ko zh  # idiomas extra
```

Los modelos quedan cacheados en el volumen `whisper-models`; el primer video del usuario ya no descarga nada y los errores de red aparecen aquí con un mensaje claro, no como un job fallido.
