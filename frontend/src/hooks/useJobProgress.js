/**
 * Hook personalizado: encapsula TODO el ciclo de vida de la conexión SSE.
 *
 * Buenas prácticas React 19:
 * - La suscripción externa vive en useEffect con función de limpieza:
 *   al desmontar (o cambiar jobId) se cierra el EventSource. Sin esto,
 *   cada video subido dejaría una conexión zombie abierta.
 * - El componente que lo usa queda declarativo: solo lee { status, progress }.
 */
import { useEffect, useState } from 'react';
import { jobEventsUrl } from '../api/client.js';

const initialState = { status: 'queued', progress: 0, result: null, error: null };

export function useJobProgress(jobId) {
  const [state, setState] = useState(initialState);

  useEffect(() => {
    if (!jobId) return;

    setState(initialState);
    const source = new EventSource(jobEventsUrl(jobId));

    const parse = (event) => JSON.parse(event.data);

    source.addEventListener('snapshot', (e) => {
      const job = parse(e);
      setState((prev) => ({ ...prev, ...job }));
    });

    source.addEventListener('progress', (e) => {
      const { progress } = parse(e);
      setState((prev) => ({ ...prev, status: 'processing', progress }));
    });

    source.addEventListener('completed', (e) => {
      const { result } = parse(e);
      setState((prev) => ({ ...prev, status: 'completed', progress: 100, result }));
      source.close();
    });

    source.addEventListener('failed', (e) => {
      const { failedReason } = parse(e);
      setState((prev) => ({ ...prev, status: 'failed', error: failedReason }));
      source.close();
    });

    return () => source.close(); // limpieza obligatoria
  }, [jobId]);

  return state;
}
