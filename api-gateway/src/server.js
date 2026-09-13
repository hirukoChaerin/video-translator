/**
 * Punto de entrada: arranque + graceful shutdown.
 *
 * El cierre ordenado importa en contenedores: Docker/Kubernetes envían
 * SIGTERM y dan ~10 s antes de SIGKILL. Cerramos el servidor HTTP primero
 * (deja de aceptar conexiones, termina las vivas) y luego la cola.
 */
import { buildApp } from './app.js';
import { config } from './config/index.js';
import { logger } from './lib/logger.js';
import { closeQueue } from './queues/video.queue.js';

const app = buildApp();
const server = app.listen(config.port, () => {
  logger.info({ port: config.port }, 'api_gateway_started');
});

// Node 24: timeouts explícitos para conexiones colgadas
server.requestTimeout = 0;      // subidas grandes: sin límite de request...
server.headersTimeout = 60_000; // ...pero headers deben llegar rápido

let shuttingDown = false;
async function shutdown(signal) {
  if (shuttingDown) return;
  shuttingDown = true;
  logger.info({ signal }, 'shutdown_started');

  server.close(async () => {
    await closeQueue();
    logger.info('shutdown_complete');
    process.exit(0);
  });

  // Red de seguridad: forzar salida si algo queda colgado
  setTimeout(() => process.exit(1), 10_000).unref();
}

process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT', () => shutdown('SIGINT'));
process.on('unhandledRejection', (reason) => {
  logger.fatal({ reason }, 'unhandled_rejection');
  shutdown('unhandledRejection');
});
