/**
 * Formulario de subida con las APIs nuevas de React 19:
 *
 * - `useActionState`: reemplaza el trío useState(loading) + useState(error) +
 *   handleSubmit manual. La acción async recibe el FormData del <form> y
 *   React gestiona pending/errores de forma declarativa.
 * - `useFormStatus` (en SubmitButton): el botón conoce el estado `pending`
 *   del formulario padre sin prop drilling.
 */
import { useActionState, useRef, useState } from 'react';
import { useFormStatus } from 'react-dom';
import { uploadVideo } from '../api/client.js';

function SubmitButton({ disabled }) {
  const { pending } = useFormStatus();
  return (
    <button className="submit" type="submit" disabled={disabled || pending}>
      {pending ? 'Subiendo video…' : 'Traducir al español'}
    </button>
  );
}

export function UploadForm({ onJobCreated }) {
  const [fileName, setFileName] = useState(null);
  const inputRef = useRef(null);

  const [error, submitAction] = useActionState(async (_prev, formData) => {
    const file = formData.get('video');
    if (!file || file.size === 0) return 'Selecciona un video primero.';

    try {
      const { jobId } = await uploadVideo(file);
      onJobCreated({ jobId, name: file.name });
      setFileName(null);
      inputRef.current?.form?.reset();
      return null; // sin error
    } catch (err) {
      return err.message;
    }
  }, null);

  return (
    <form action={submitAction} className="upload-form">
      <label className="dropzone">
        <input
          ref={inputRef}
          type="file"
          name="video"
          accept="video/mp4,video/quicktime,video/x-matroska,video/webm"
          onChange={(e) => setFileName(e.target.files?.[0]?.name ?? null)}
        />
        {fileName ? (
          <span className="dropzone-file">{fileName}</span>
        ) : (
          <span className="dropzone-hint">
            Elige un video o arrástralo aquí
            <small>MP4, MOV, MKV o WebM · hasta 1 GB</small>
          </span>
        )}
      </label>

      <SubmitButton disabled={!fileName} />

      {error && <p className="form-error" role="alert">{error}</p>}
    </form>
  );
}
