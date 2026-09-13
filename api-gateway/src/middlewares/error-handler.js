/**
 * Manejador central de errores.
 *
 * Express 5 propaga automáticamente los rechazos de handlers async a este
 * middleware (adiós a los wrappers catchAsync de Express 4).
 */
import { logger } from '../lib/logger.js';

export function notFound(_req, res) {
  res.status(404).json({ error: 'Recurso no encontrado' });
}

// eslint-disable-next-line no-unused-vars
export function errorHandler(err, req, res, _next) {
  const status = err.status ?? (err.name === 'MulterError' ? 413 : 500);

  // Log completo en servidor, mensaje seguro al cliente.
  logger.error({ err, path: req.path, status }, 'request_failed');

  res.status(status).json({
    error: status >= 500 ? 'Error interno del servidor' : err.message,
  });
}
