/**
 * Cola de trabajos de traducción de video.
 *
 * Patrones aplicados:
 * - Singleton por módulo: los módulos ESM se evalúan una sola vez, así que
 *   `videoQueue` y `videoQueueEvents` son instancias únicas por proceso
 *   (evita abrir decenas de conexiones Redis por request).
 * - Observer: QueueEvents emite `progress`, `completed` y `failed`; las rutas
 *   SSE se suscriben sin acoplarse al worker de Python.
 */
import { Queue, QueueEvents } from 'bullmq';
import { config } from '../config/index.js';
import { redisConnection } from '../lib/redis.js';

export const videoQueue = new Queue(config.queueName, {
  connection: redisConnection,
  defaultJobOptions: {
    attempts: 3,
    backoff: { type: 'exponential', delay: 5_000 },
    // Limpieza automática: Redis vive en RAM, no acumulamos historiales enormes.
    removeOnComplete: { age: 24 * 3600, count: 500 },
    removeOnFail: { age: 7 * 24 * 3600 },
  },
});

export const videoQueueEvents = new QueueEvents(config.queueName, {
  connection: redisConnection,
});

/** Cierre ordenado: lo invoca server.js en el graceful shutdown. */
export async function closeQueue() {
  await Promise.allSettled([videoQueue.close(), videoQueueEvents.close()]);
}
