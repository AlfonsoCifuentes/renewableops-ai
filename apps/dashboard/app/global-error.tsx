"use client";

export default function GlobalError({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="es">
      <body>
        <main className="error-page">
          <h1>RenewableOps necesita reiniciarse</h1>
          <p>Se ha producido un error inesperado en la interfaz.</p>
          <button type="button" onClick={reset}>Reintentar</button>
        </main>
      </body>
    </html>
  );
}
