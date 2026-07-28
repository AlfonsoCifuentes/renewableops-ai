"use client";

import { RefreshCcw, TriangleAlert } from "lucide-react";

export default function ErrorPage({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main className="error-page">
      <TriangleAlert size={28} />
      <p className="eyebrow">Error de lectura</p>
      <h1>No se pudo abrir el snapshot</h1>
      <p>Comprueba que el pipeline de demostración se ha ejecutado y vuelve a intentarlo.</p>
      <button type="button" className="button button-primary" onClick={reset}>
        <RefreshCcw size={15} /> Reintentar
      </button>
    </main>
  );
}
