/**
 * Logger estructurado con pino.
 * JSON en producción (fácil de indexar en ELK/Loki), legible en desarrollo.
 * Un logger singleton evita crear streams duplicados (ahorra memoria).
 */
import pino from 'pino';
import { config } from '../config/index.js';

export const logger = pino({
  level: config.env === 'production' ? 'info' : 'debug',
  base: { service: 'api-gateway' },
});
