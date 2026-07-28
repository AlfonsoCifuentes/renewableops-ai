import Link from "next/link";

export default function NotFound() {
  return (
    <main className="error-page">
      <p className="eyebrow">404</p>
      <h1>Ese módulo no existe</h1>
      <p>Vuelve al centro de operaciones para continuar la exploración.</p>
      <Link className="button button-primary" href="/">Volver a Overview</Link>
    </main>
  );
}
