/**
 * Endpoints internos (worker -> api-gateway).
 *
 * El worker de Python notifica aquí cuando termina. Aunque BullMQ ya nos da
 * eventos vía Redis, este webhook deja un punto de extensión explícito:
 * enviar email al usuario, disparar métricas, invalidar cachés, etc.
 */
import { Router } from 'express';
import { internalAuth } from '../middlewares/internal-auth.js';
import { logger } from '../lib/logger.js';

export const internalRouter = Router();

internalRouter.use(internalAuth);

internalRouter.post('/jobs/:id/finished', (req, res) => {
  const { id } = req.params;
  const { status, artifacts, error } = req.body ?? {};

  logger.info({ jobId: id, status, artifacts, error }, 'worker_notification');
  // Punto de extensión: notificaciones push/email, métricas, etc.

  res.status(204).end();
});
