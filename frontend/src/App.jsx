/**
 * Componente raíz.
 * Estado mínimo: solo la lista de trabajos creados en esta sesión.
 * Cada JobCard gestiona su propia conexión SSE de forma aislada.
 */
import { useState } from 'react';
import { UploadForm } from './components/UploadForm.jsx';
import { JobCard } from './components/JobCard.jsx';
//default app
export default function App() {
  const [jobs, setJobs] = useState([]);

  const addJob = (job) => setJobs((prev) => [job, ...prev]);

  return (
    <main className="page">
      <header className="hero">
        <p className="hero-band">— y ahora tus videos hablan español —</p>
        <h1>Subtitulador</h1>
        <p className="hero-copy">
          Sube un video en cualquier idioma. Lo transcribimos con Whisper,
          lo traducimos y te devolvemos los subtítulos en español, listos
          para descargar o ya incrustados en el video.
        </p>
      </header>

      <UploadForm onJobCreated={addJob} />

      {jobs.length > 0 && (
        <section className="jobs" aria-label="Trabajos">
          {jobs.map((job) => (
            <JobCard key={job.jobId} jobId={job.jobId} name={job.name} />
          ))}
        </section>
      )}
    </main>
  );
}
