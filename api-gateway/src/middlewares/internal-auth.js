/**
 * Autenticación simple por token compartido para endpoints internos
 * (callbacks del worker). En producción con Kubernetes esto se reemplaza
 * por red interna + mTLS o un service mesh, pero el patrón queda igual.
 */
import crypto from 'node:crypto';
import { config } from '../config/index.js';

export function internalAuth(req, res, next) {
  const token = req.get('x-internal-token') ?? '';
  const expected = config.internalToken;
  const valid =
    token.length === expected.length &&
    crypto.timingSafeEqual(Buffer.from(token), Buffer.from(expected));

  if (!valid) return res.status(401).json({ error: 'No autorizado' });
  next();
}
