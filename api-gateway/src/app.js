/**
 * Composición de la aplicación Express (sin efectos de red).
 * Separar app de server permite testear con supertest sin abrir puertos.
 */
import express from 'express';
import helmet from 'helmet';
import cors from 'cors';
import { pinoHttp } from 'pino-http';
import { config } from './config/index.js';
import { logger } from './lib/logger.js';
import { jobsRouter } from './routes/jobs.routes.js';
import { internalRouter } from './routes/internal.routes.js';
import { errorHandler, notFound } from './middlewares/error-handler.js';

export function buildApp() {
  const app = express();

  app.disable('x-powered-by');
  app.use(helmet());
  app.use(cors({ origin: config.corsOrigin }));
  app.use(express.json({ limit: '100kb' })); // JSON pequeño; los videos van por multer
  app.use(pinoHttp({ logger, autoLogging: { ignore: (req) => req.url === '/health' } }));

  app.get('/health', (_req, res) => res.json({ status: 'ok' }));

  app.use('/api/jobs', jobsRouter);
  app.use('/internal', internalRouter);

  app.use(notFound);
  app.use(errorHandler);

  return app;
}
