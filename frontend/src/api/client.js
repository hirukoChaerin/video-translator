/**
 * Cliente HTTP mínimo: una sola responsabilidad por función y cero
 * dependencias (fetch y EventSource son nativos).
 */
const BASE = '/api';

export async function uploadVideo(file) {
  const form = new FormData();
  form.append('video', file);

  const res = await fetch(`${BASE}/jobs`, { method: 'POST', body: form });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error ?? `Error al subir el video (${res.status})`);
  }
  return res.json(); // { jobId, status }
}

export function jobEventsUrl(jobId) {
  return `${BASE}/jobs/${jobId}/events`;
}

export function downloadUrl(jobId, kind) {
  return `${BASE}/jobs/${jobId}/download/${kind}`;
}
