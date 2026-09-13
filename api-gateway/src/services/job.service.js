/**
 * Capa de servicio: toda la lógica de negocio de "trabajos".
 *
 * Los controladores/rutas solo traducen HTTP <-> servicio; esta capa no sabe
 * nada de req/res, por lo que se puede testear sin levantar Express y se
 * puede reutilizar (CLI, gRPC, tests) sin cambios.
 */
import crypto from 'node:crypto';
import path from 'node:path';
import fs from 'node:fs/promises';
import { videoQueue } from '../queues/video.queue.js';
import { config } from '../config/index.js';

/** Estados normalizados que consume el frontend. */
export const JobStatus = Object.freeze({
  QUEUED: 'queued',
  PROCESSING: 'processing',
  COMPLETED: 'completed',
  FAILED: 'failed',
});

const bullStateToStatus = {
  waiting: JobStatus.QUEUED,
  delayed: JobStatus.QUEUED,
  active: JobStatus.PROCESSING,
  completed: JobStatus.COMPLETED,
  failed: JobStatus.FAILED,
};

/**
 * Encola un video ya guardado en disco por multer.
 * @param {{ path: string, originalname: string, size: number }} file
 */
export async function enqueueVideo(file) {
  const jobId = crypto.randomUUID(); // nativo en Node 24, sin dependencias

  await videoQueue.add(
    'translate-video',
    {
      jobId,
      inputPath: file.path,
      originalName: file.originalname,
      sizeBytes: file.size,
      outputDir: path.join(config.storage.outputs, jobId),
    },
    { jobId }, // id determinista: permite consultar el job por su UUID
  );

  return { jobId, status: JobStatus.QUEUED };
}

/** Devuelve una vista pública del job (nunca exponemos rutas internas del disco). */
export async function getJob(jobId) {
  const job = await videoQueue.getJob(jobId);
  if (!job) return null;

  const state = await job.getState();
  return {
    jobId,
    status: bullStateToStatus[state] ?? state,
    progress: typeof job.progress === 'number' ? job.progress : 0,
    originalName: job.data.originalName,
    result: job.returnvalue ?? null,
    failedReason: job.failedReason ?? null,
    createdAt: job.timestamp,
    finishedAt: job.finishedOn ?? null,
  };
}

/**
 * Resuelve un artefacto descargable validando que el archivo exista y
 * que esté dentro del directorio de salidas (evita path traversal).
 */
export async function resolveArtifact(jobId, kind) {
  const job = await videoQueue.getJob(jobId);
  const artifacts = job?.returnvalue?.artifacts;
  const relative = artifacts?.[kind];
  if (!relative) return null;

  const absolute = path.resolve(config.storage.outputs, relative);
  if (!absolute.startsWith(config.storage.outputs)) return null; // defensa extra

  try {
    await fs.access(absolute);
    return absolute;
  } catch {
    return null;
  }
}
