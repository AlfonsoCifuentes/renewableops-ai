import type { ReactNode } from "react";
import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";

interface PanelProps {
  title?: string;
  eyebrow?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function Panel({
  title,
  eyebrow,
  action,
  children,
  className = "",
}: PanelProps) {
  return (
    <section className={`panel ${className}`}>
      {title || eyebrow || action ? (
        <header className="panel-header">
          <div>
            {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
            {title ? <h2>{title}</h2> : null}
          </div>
          {action ? <div className="panel-action">{action}</div> : null}
        </header>
      ) : null}
      {children}
    </section>
  );
}

interface KpiCardProps {
  label: string;
  value: string;
  context: string;
  trend?: number;
  tone?: "default" | "warning" | "good";
  icon: ReactNode;
  onInfo?: () => void;
}

export function KpiCard({
  label,
  value,
  context,
  trend,
  tone = "default",
  icon,
  onInfo,
}: KpiCardProps) {
  const TrendIcon =
    trend === undefined || trend === 0
      ? Minus
      : trend > 0
        ? ArrowUpRight
        : ArrowDownRight;
  return (
    <article className={`kpi-card kpi-${tone}`}>
      <div className="kpi-top">
        <button
          type="button"
          className="kpi-label"
          onClick={onInfo}
          disabled={!onInfo}
          aria-label={onInfo ? `Definición de ${label}` : undefined}
        >
          {label}
        </button>
        <span className="kpi-icon" aria-hidden="true">
          {icon}
        </span>
      </div>
      <strong>{value}</strong>
      <div className="kpi-context">
        {trend !== undefined ? (
          <span className={`trend ${trend >= 0 ? "trend-up" : "trend-down"}`}>
            <TrendIcon size={13} />
            {Math.abs(trend).toLocaleString("es-ES", { maximumFractionDigits: 1 })}%
          </span>
        ) : null}
        <span>{context}</span>
      </div>
    </article>
  );
}

export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "success" | "warning" | "critical" | "info";
}) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

export function StatusDot({ status }: { status: string }) {
  const tone = ["healthy", "success", "fresh", "passed", "online", "verified"].includes(
    status,
  )
    ? "success"
    : ["critical", "failed", "offline"].includes(status)
      ? "critical"
      : "warning";
  return (
    <span className={`status-dot status-${tone}`}>
      <i aria-hidden="true" />
      {status.replaceAll("_", " ")}
    </span>
  );
}

export function Sparkline({
  values,
  tone = "green",
}: {
  values: number[];
  tone?: "green" | "rust";
}) {
  const width = 96;
  const height = 30;
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const span = Math.max(max - min, 1);
  const points = values
    .map((value, index) => {
      const x = (index / Math.max(values.length - 1, 1)) * width;
      const y = height - ((value - min) / span) * (height - 4) - 2;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  return (
    <svg
      className={`sparkline sparkline-${tone}`}
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label="Tendencia reciente"
    >
      <polyline points={points} fill="none" stroke="currentColor" strokeWidth="1.7" />
    </svg>
  );
}

export function EmptyState({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="empty-state">
      <span aria-hidden="true">∅</span>
      <strong>{title}</strong>
      <p>{description}</p>
    </div>
  );
}
