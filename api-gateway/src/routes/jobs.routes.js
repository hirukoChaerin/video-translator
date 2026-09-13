/**
 * Rutas públicas del recurso /api/jobs.
 *
 * - POST   /api/jobs            -> sube el video y encola el trabajo
 * - GET    /api/jobs/:id        -> estado puntual (polling / recarga de página)
 * - GET    /api/jobs/:id/events -> Server-Sent Events con progreso en vivo
 * - GET    /api/jobs/:id/download/:kind -> descarga (video | srt | vtt)
 *
 * SSE vs WebSockets: para un flujo unidireccional servidor->cliente, SSE es
 * más barato (HTTP plano, reconexión automática nativa) y no requiere
 * dependencias extra. Con Express 5 los handlers async fluyen al error handler.
 */
import { Router } from 'express';
import path from 'node:path';
import { uploadVideo } from '../middlewares/upload.js';
import { videoQueueEvents } from '../queues/video.queue.js';
import { enqueueVideo, getJob, resolveArtifact, JobStatus } from '../services/job.service.js';

export const jobsRouter = Router();

jobsRouter.post('/', uploadVideo, async (req, res) => {
  if (!req.file) {
    return res.status(400).json({ error: 'Falta el campo "video" en el formulario' });
  }
  const job = await enqueueVideo(req.file);
  res.status(202).json(job); // 202 Accepted: el trabajo es asíncrono
});

jobsRouter.get('/:id', async (req, res) => {
  const job = await getJob(req.params.id);
  if (!job) return res.status(404).json({ error: 'Trabajo no encontrado' });
  res.json(job);
});

jobsRouter.get('/:id/events', async (req, res) => {
  const { id } = req.params;
  const job = await getJob(id);
  if (!job) return res.status(404).json({ error: 'Trabajo no encontrado' });

  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache, no-transform',
    Connection: 'keep-alive',
  });

  const send = (event, data) =>
    res.write(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);

  send('snapshot', job); // estado inicial inmediato

  // Observer: nos suscribimos a los eventos globales de la cola y filtramos
  // por jobId. Un solo QueueEvents sirve a todas las conexiones SSE.
  const onProgress = ({ jobId, data }) => {
    if (jobId === id) send('progress', { progress: data });
  };
  const onCompleted = ({ jobId, returnvalue }) => {
    if (jobId === id) {
      send('completed', { status: JobStatus.COMPLETED, result: returnvalue });
      res.end();
    }
  };
  const onFailed = ({ jobId, failedReason }) => {
    if (jobId === id) {
      send('failed', { status: JobStatus.FAILED, failedReason });
      res.end();
    }
  };

  videoQueueEvents.on('progress', onProgress);
  videoQueueEvents.on('completed', onCompleted);
  videoQueueEvents.on('failed', onFailed);

  // Heartbeat cada 25 s para que proxies no corten la conexión.
  const heartbeat = setInterval(() => res.write(': ping\n\n'), 25_000);

  // Limpieza SIEMPRE al cerrar: sin esto habría fuga de listeners y memoria.
  req.on('close', () => {
    clearInterval(heartbeat);
    videoQueueEvents.off('progress', onProgress);
    videoQueueEvents.off('completed', onCompleted);
    videoQueueEvents.off('failed', onFailed);
  });
});

jobsRouter.get('/:id/download/:kind', async (req, res) => {
  const { id, kind } = req.params;
  if (!['video', 'srt', 'vtt'].includes(kind)) {
    return res.status(400).json({ error: 'Tipo de artefacto inválido' });
  }
  const filePath = await resolveArtifact(id, kind);
  if (!filePath) return res.status(404).json({ error: 'Artefacto no disponible' });

  // res.download hace streaming desde disco: RAM constante sin importar el tamaño.
  res.download(filePath, path.basename(filePath));
});
