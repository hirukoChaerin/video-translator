/**
 * Subida de archivos con multer 2 en modo diskStorage.
 *
 * Clave para la RAM: diskStorage hace *streaming* del body directamente al
 * disco. Nunca cargamos el video completo en memoria (memoryStorage sería
 * un desastre con archivos de 1 GB).
 */
import path from 'node:path';
import fs from 'node:fs';
import crypto from 'node:crypto';
import multer from 'multer';
import { config } from '../config/index.js';

const ALLOWED_MIME = new Set([
  'video/mp4',
  'video/quicktime',
  'video/x-matroska',
  'video/webm',
  'video/x-msvideo',
]);

fs.mkdirSync(config.storage.uploads, { recursive: true });

const storage = multer.diskStorage({
  destination: config.storage.uploads,
  filename: (_req, file, cb) => {
    // Nunca confiar en el nombre original: generamos uno propio y
    // conservamos solo la extensión saneada.
    const ext = path.extname(file.originalname).toLowerCase().slice(0, 10);
    cb(null, `${crypto.randomUUID()}${ext}`);
  },
});

export const uploadVideo = multer({
  storage,
  limits: { fileSize: config.maxUploadBytes, files: 1 },
  fileFilter: (_req, file, cb) => {
    if (ALLOWED_MIME.has(file.mimetype)) return cb(null, true);
    const error = new Error(`Tipo de archivo no soportado: ${file.mimetype}`);
    error.status = 415;
    cb(error);
  },
}).single('video');
