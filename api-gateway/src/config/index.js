/**
 * Configuración centralizada e inmutable.
 *
 * Buenas prácticas aplicadas:
 * - Un único punto de lectura de process.env: el resto del código nunca
 *   toca variables de entorno directamente (fácil de testear y de auditar).
 * - Object.freeze evita mutaciones accidentales en runtime.
 * - Valores por defecto sensatos + validación temprana (fail fast).
 */
import path from 'node:path';

const required = (name, fallback) => {
  const value = process.env[name] ?? fallback;
  if (value === undefined) {
    throw new Error(`Variable de entorno requerida: ${name}`);
  }
  return value;
};

export const config = Object.freeze({
  env: process.env.NODE_ENV ?? 'development',
  port: Number(process.env.PORT ?? 4000),

  redis: Object.freeze({
    host: required('REDIS_HOST', '127.0.0.1'),
    port: Number(process.env.REDIS_PORT ?? 6379),
  }),

  queueName: process.env.QUEUE_NAME ?? 'video-translation',

  storage: Object.freeze({
    root: path.resolve(required('STORAGE_ROOT', './storage')),
    get uploads() { return path.join(this.root, 'uploads'); },
    get outputs() { return path.join(this.root, 'outputs'); },
  }),

  maxUploadBytes: Number(process.env.MAX_UPLOAD_MB ?? 1024) * 1024 * 1024,
  corsOrigin: process.env.CORS_ORIGIN ?? 'http://localhost:5173',
  internalToken: required('INTERNAL_TOKEN', 'dev-token'),
});
