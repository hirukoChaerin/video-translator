/**
 * Opciones de conexión compartidas para BullMQ.
 * BullMQ crea sus propias conexiones ioredis a partir de este objeto;
 * `maxRetriesPerRequest: null` es requerido por BullMQ para los blocking commands.
 */
import { config } from '../config/index.js';

export const redisConnection = {
  host: config.redis.host,
  port: config.redis.port,
  maxRetriesPerRequest: null,
};
