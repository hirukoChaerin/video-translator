/**
 * Tarjeta de un trabajo en curso o terminado.
 * Componente de presentación: todo el estado en vivo viene del hook
 * useJobProgress; aquí solo se decide qué pintar según el estado.
 */
import { useJobProgress } from '../hooks/useJobProgress.js';
import { downloadUrl } from '../api/client.js';

const STAGES = [
  [0, 'En cola'],
  [1, 'Extrayendo audio'],
  [10, 'Transcribiendo con Whisper'],
  [60, 'Traduciendo al español'],
  [75, 'Generando subtítulos'],
  [80, 'Renderizando video final'],
];

function stageLabel(progress) {
  let label = STAGES[0][1];
  for (const [threshold, text] of STAGES) {
    if (progress >= threshold) label = text;
  }
  return label;
}

export function JobCard({ jobId, name }) {
  const { status, progress, result, error } = useJobProgress(jobId);

  return (
    <article className={`job-card job-${status}`}>
      <header>
        <h3>{name}</h3>
        <span className="job-status">
          {status === 'completed' && 'Listo'}
          {status === 'failed' && 'Falló'}
          {status === 'processing' && `${progress}%`}
          {status === 'queued' && 'En cola'}
        </span>
      </header>

      {status !== 'completed' && status !== 'failed' && (
        <>
          <div
            className="timeline"
            role="progressbar"
            aria-valuenow={progress}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            <div className="timeline-fill" style={{ width: `${progress}%` }} />
            <div className="timeline-head" style={{ left: `${progress}%` }} />
          </div>
          <p className="job-stage">{stageLabel(progress)}</p>
        </>
      )}

      {status === 'completed' && result && (
        <div className="job-downloads">
          {result.artifacts?.video && (
            <a href={downloadUrl(jobId, 'video')}>Descargar video subtitulado</a>
          )}
          {result.artifacts?.srt && <a href={downloadUrl(jobId, 'srt')}>Archivo .srt</a>}
          {result.artifacts?.vtt && <a href={downloadUrl(jobId, 'vtt')}>Archivo .vtt</a>}
          <p className="job-meta">
            Idioma detectado: {result.sourceLanguage} · {result.segments} segmentos
          </p>
        </div>
      )}

      {status === 'failed' && (
        <p className="form-error">
          No se pudo procesar el video. {error ? `Detalle: ${error}` : 'Intenta de nuevo.'}
        </p>
      )}
    </article>
  );
}
