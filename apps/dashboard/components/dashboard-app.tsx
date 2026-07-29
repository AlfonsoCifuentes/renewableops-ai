"use client";

import {
  Activity,
  Bell,
  Boxes,
  ChartNoAxesCombined,
  ChevronDown,
  CircleGauge,
  Database,
  FlaskConical,
  Grid2X2,
  HeartPulse,
  Images,
  Menu,
  Moon,
  PanelLeftClose,
  PanelLeftOpen,
  RadioTower,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  SunMedium,
  Wind,
  X,
  Zap,
} from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { AssetHealth } from "@/components/asset-health";
import { DataExplorer, DataQuality, Mlops } from "@/components/data-pages";
import { Fleet } from "@/components/fleet";
import { Forecasting } from "@/components/forecasting";
import { Inspections } from "@/components/inspections";
import { Market } from "@/components/market";
import { Overview } from "@/components/overview";
import { Governance, Observability, ScenarioLab } from "@/components/platform-pages";
import { Badge, Sparkline, StatusDot } from "@/components/ui";
import { formatCurrency, formatDate, formatNumber } from "@/lib/format";
import type {
  Asset,
  DashboardSnapshot,
  GlobalFilters,
  SectionId,
} from "@/lib/types";

const NAV_GROUPS = [
  {
    label: "Operaciones",
    items: [
      { id: "overview", label: "Overview", icon: Grid2X2 },
      { id: "fleet", label: "Fleet", icon: Boxes },
      { id: "asset-health", label: "Asset Health", icon: HeartPulse },
    ],
  },
  {
    label: "Analytics",
    items: [
      { id: "forecast-solar", label: "Forecast Solar", icon: SunMedium },
      { id: "forecast-wind", label: "Forecast Wind", icon: Wind },
      { id: "market", label: "Market", icon: ChartNoAxesCombined },
      { id: "inspections", label: "Visual Inspections", icon: Images },
    ],
  },
  {
    label: "Plataforma",
    items: [
      { id: "data-explorer", label: "Data Explorer", icon: Database },
      { id: "data-quality", label: "Data Quality", icon: CircleGauge },
      { id: "mlops", label: "MLOps", icon: Activity },
      { id: "observability", label: "Observability", icon: RadioTower },
      { id: "governance", label: "Governance", icon: ShieldCheck },
      { id: "scenario-lab", label: "Scenario Lab", icon: FlaskConical },
    ],
  },
] as const;

function sectionPath(section: string): string {
  return section === "overview" ? "/" : `/${section}`;
}

export function DashboardApp({
  data,
  initialSection,
}: {
  data: DashboardSnapshot;
  initialSection: SectionId;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [selectedAsset, setSelectedAsset] = useState<Asset | null>(null);
  const [sourceModal, setSourceModal] = useState(false);
  const [definitionId, setDefinitionId] = useState<string | null>(null);
  const [noticeOpen, setNoticeOpen] = useState(false);

  const periodParam = searchParams.get("period");
  const technologyParam = searchParams.get("technology");
  const regionParam = searchParams.get("region");
  const filters: GlobalFilters = useMemo(
    () => ({
      period: (periodParam as GlobalFilters["period"]) ?? "7d",
      technology:
        (technologyParam as GlobalFilters["technology"]) ?? "all",
      region: regionParam ?? "all",
    }),
    [periodParam, regionParam, technologyParam],
  );
  const regions = useMemo(
    () => [...new Set(data.assets.map((asset) => asset.region))].toSorted(),
    [data.assets],
  );
  const visibleAssets = useMemo(
    () =>
      data.assets.filter(
        (asset) =>
          (filters.technology === "all" || asset.technology === filters.technology) &&
          (filters.region === "all" || asset.region === filters.region),
      ),
    [data.assets, filters.region, filters.technology],
  );
  const activeFilters =
    Number(filters.period !== "7d") +
    Number(filters.technology !== "all") +
    Number(filters.region !== "all");

  const updateFilters = useCallback(
    (patch: Partial<GlobalFilters>) => {
      const next = { ...filters, ...patch };
      const params = new URLSearchParams(searchParams.toString());
      for (const [key, value] of Object.entries(next)) {
        if (
          (key === "period" && value === "7d") ||
          (key !== "period" && value === "all")
        ) {
          params.delete(key);
        } else {
          params.set(key, value);
        }
      }
      const query = params.toString();
      router.replace(`${pathname}${query ? `?${query}` : ""}`, { scroll: false });
    },
    [filters, pathname, router, searchParams],
  );

  useEffect(() => {
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setSelectedAsset(null);
        setSourceModal(false);
        setDefinitionId(null);
        setMobileOpen(false);
      }
    }
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, []);

  function navigate(path: string) {
    setMobileOpen(false);
    router.push(path);
  }

  function toggleTheme() {
    const next = document.documentElement.dataset.theme !== "dark";
    document.documentElement.dataset.theme = next ? "dark" : "light";
    window.localStorage.setItem("renewableops-theme", next ? "dark" : "light");
  }

  const section = (() => {
    const common = {
      data,
    };
    switch (initialSection) {
      case "overview":
        return (
          <Overview
            {...common}
            assets={visibleAssets}
            onAssetSelect={setSelectedAsset}
            onDefinition={setDefinitionId}
            onSourceOpen={() => setSourceModal(true)}
            onNavigate={navigate}
          />
        );
      case "fleet":
        return <Fleet assets={visibleAssets} onAssetSelect={setSelectedAsset} />;
      case "forecast-solar":
        return <Forecasting {...common} technology="solar" />;
      case "forecast-wind":
        return <Forecasting {...common} technology="wind" />;
      case "market":
        return <Market {...common} />;
      case "asset-health":
        return <AssetHealth {...common} onAssetSelect={setSelectedAsset} />;
      case "inspections":
        return <Inspections {...common} />;
      case "data-explorer":
        return <DataExplorer {...common} />;
      case "data-quality":
        return <DataQuality {...common} />;
      case "mlops":
        return <Mlops {...common} />;
      case "observability":
        return <Observability {...common} />;
      case "governance":
        return <Governance {...common} />;
      case "scenario-lab":
        return <ScenarioLab {...common} />;
    }
  })();

  return (
    <div className={`app-shell ${collapsed ? "sidebar-collapsed" : ""}`}>
      <aside className={`sidebar ${mobileOpen ? "mobile-open" : ""}`}>
        <div className="brand">
          <button
            type="button"
            className="brand-mark"
            onClick={() => navigate("/")}
            aria-label="Ir a Overview"
          >
            <svg viewBox="0 0 42 42" aria-hidden="true">
              <path d="M8 29.5C17 29.5 20.5 24 20.5 14.5C29.5 14.5 34 20 34 28" />
              <path d="M12 33C18 25 25 23 33 24" />
            </svg>
          </button>
          <div>
            <strong>RenewableOps</strong>
            <span>AI control room</span>
          </div>
          <button
            type="button"
            className="icon-button sidebar-close-mobile"
            onClick={() => setMobileOpen(false)}
            aria-label="Cerrar navegación"
          >
            <X size={18} />
          </button>
        </div>
        <nav className="main-nav" aria-label="Navegación principal">
          {NAV_GROUPS.map((group) => (
            <div className="nav-group" key={group.label}>
              <p>{group.label}</p>
              {group.items.map((item) => {
                const Icon = item.icon;
                const active = item.id === initialSection;
                return (
                  <button
                    type="button"
                    key={item.id}
                    className={active ? "is-active" : ""}
                    onClick={() => navigate(sectionPath(item.id))}
                    aria-current={active ? "page" : undefined}
                    title={collapsed ? item.label : undefined}
                  >
                    <Icon size={16} strokeWidth={1.8} />
                    <span>{item.label}</span>
                    {item.id === "asset-health" && data.anomalies.length ? (
                      <i className="nav-count">{data.anomalies.length}</i>
                    ) : null}
                  </button>
                );
              })}
            </div>
          ))}
        </nav>
        <div className="sidebar-meta">
          <div className="environment-card">
            <span><i /> Demo environment</span>
            <strong>Snapshot valid</strong>
            <small>{formatDate(data.meta.generated_at, true)} CEST</small>
          </div>
          <button
            type="button"
            className="collapse-button"
            onClick={() => setCollapsed((value) => !value)}
            aria-label={collapsed ? "Expandir barra lateral" : "Contraer barra lateral"}
          >
            {collapsed ? <PanelLeftOpen size={16} /> : <PanelLeftClose size={16} />}
            <span>Contraer</span>
          </button>
        </div>
      </aside>

      {mobileOpen ? <button type="button" className="mobile-backdrop" aria-label="Cerrar navegación" onClick={() => setMobileOpen(false)} /> : null}

      <div className="app-main">
        <header className="topbar">
          <button
            type="button"
            className="icon-button mobile-menu"
            onClick={() => setMobileOpen(true)}
            aria-label="Abrir navegación"
          >
            <Menu size={18} />
          </button>
          <button
            type="button"
            className="command-trigger"
            onClick={() => setNoticeOpen(true)}
            aria-label="Buscar activo, métrica o incidencia"
          >
            <Search size={15} />
            <span>Buscar activo, métrica o incidencia</span>
            <kbd>⌘ K</kbd>
          </button>
          <div className="topbar-status">
            <button type="button" className="snapshot-status" onClick={() => setSourceModal(true)}>
              <i />
              <span>Datos válidos</span>
              <small>hace {data.kpis.data_freshness_minutes} min</small>
            </button>
            <button type="button" className="icon-button" onClick={toggleTheme} aria-label="Cambiar tema de color">
              <Moon size={16} />
            </button>
            <button type="button" className="icon-button notification-button" onClick={() => setNoticeOpen(true)} aria-label="Notificaciones">
              <Bell size={16} /><i />
            </button>
            <div className="operator-avatar" title="Portfolio operator">AC</div>
          </div>
        </header>

        <section className="filterbar" aria-label="Filtros globales">
          <button type="button" className="filter-mobile-toggle" onClick={() => setFiltersOpen((value) => !value)}>
            <SlidersHorizontal size={15} /> Filtros {activeFilters ? `(${activeFilters})` : ""}
          </button>
          <div className={`filter-controls ${filtersOpen ? "is-open" : ""}`}>
            <label>
              <span>Periodo</span>
              <select value={filters.period} onChange={(event) => updateFilters({ period: event.target.value as GlobalFilters["period"] })}>
                <option value="24h">24 horas</option>
                <option value="7d">7 días</option>
                <option value="30d">30 días</option>
              </select>
              <ChevronDown size={13} />
            </label>
            <label>
              <span>Tecnología</span>
              <select value={filters.technology} onChange={(event) => updateFilters({ technology: event.target.value as GlobalFilters["technology"] })}>
                <option value="all">Todas</option>
                <option value="solar">Solar</option>
                <option value="wind">Eólica</option>
                <option value="battery">Batería</option>
              </select>
              <ChevronDown size={13} />
            </label>
            <label>
              <span>Región</span>
              <select value={filters.region} onChange={(event) => updateFilters({ region: event.target.value })}>
                <option value="all">Todas</option>
                {regions.map((region) => <option key={region} value={region}>{region}</option>)}
              </select>
              <ChevronDown size={13} />
            </label>
            {activeFilters ? (
              <button type="button" className="reset-filters" onClick={() => updateFilters({ period: "7d", technology: "all", region: "all" })}>
                <X size={13} /> Restablecer
              </button>
            ) : null}
          </div>
          <div className="filter-context">
            <Badge tone="neutral">{visibleAssets.length} activos</Badge>
            <span>Europe/Madrid · Snapshot público</span>
          </div>
        </section>

        <main className="page-content">{section}</main>
        <footer className="app-footer">
          <div><Zap size={14} /><strong>RenewableOps AI</strong><span>Decision support only · No controla equipos reales</span></div>
          <div><span>Snapshot {data.meta.snapshot_version}</span><span>{data.meta.pipeline_run_id}</span></div>
        </footer>
      </div>

      {selectedAsset ? (
        <div className="drawer-layer" role="dialog" aria-modal="true" aria-label={`Detalle de ${selectedAsset.name}`}>
          <button className="drawer-backdrop" type="button" onClick={() => setSelectedAsset(null)} aria-label="Cerrar detalle" />
          <aside className="asset-drawer">
            <header>
              <div>
                <p className="eyebrow">{selectedAsset.code} · {selectedAsset.technology_label}</p>
                <h2>{selectedAsset.name}</h2>
                <span>{selectedAsset.municipality}, {selectedAsset.region}</span>
              </div>
              <button type="button" className="icon-button" onClick={() => setSelectedAsset(null)} aria-label="Cerrar"><X size={17} /></button>
            </header>
            <div className="drawer-status">
              <StatusDot status={selectedAsset.status} />
              <span>Última telemetría hace 7 min</span>
            </div>
            <div className="drawer-chart">
              <Sparkline values={selectedAsset.sparkline} tone={selectedAsset.mwh_at_risk > 10 ? "rust" : "green"} />
            </div>
            <div className="drawer-metrics">
              <div><span>Potencia actual</span><strong>{formatNumber(selectedAsset.current_power_mw)} MW</strong></div>
              <div><span>Capacidad</span><strong>{formatNumber(selectedAsset.capacity_mw)} MW</strong></div>
              <div><span>Disponibilidad</span><strong>{formatNumber(selectedAsset.availability)}%</strong></div>
              <div><span>Factor capacidad</span><strong>{formatNumber(selectedAsset.capacity_factor)}%</strong></div>
              <div><span>Forecast 24 h</span><strong>{formatNumber(selectedAsset.forecast_24h_mwh)} MWh</strong></div>
              <div><span>Ingreso 7 d</span><strong>{formatCurrency(selectedAsset.revenue_7d_eur)}</strong></div>
            </div>
            {selectedAsset.mwh_at_risk > 0 ? (
              <div className="drawer-alert">
                <HeartPulse size={17} />
                <div><strong>{formatNumber(selectedAsset.mwh_at_risk)} MWh en riesgo</strong><span>Revisar evidencia antes de actuar.</span></div>
              </div>
            ) : null}
            <div className="drawer-technical">
              <h3>Ficha técnica</h3>
              <dl>
                <div><dt>Fabricante</dt><dd>{selectedAsset.manufacturer}</dd></div>
                <div><dt>Modelo</dt><dd>{selectedAsset.model}</dd></div>
                <div><dt>Portfolio</dt><dd>{selectedAsset.portfolio}</dd></div>
                <div><dt>En servicio</dt><dd>{selectedAsset.commissioning_date}</dd></div>
                <div><dt>Última inspección</dt><dd>{selectedAsset.last_inspection}</dd></div>
              </dl>
            </div>
            <button type="button" className="button button-primary full-width" onClick={() => { setSelectedAsset(null); navigate("/asset-health"); }}>
              Abrir salud del activo
            </button>
          </aside>
        </div>
      ) : null}

      {sourceModal ? (
        <Modal title="Fuentes y freshness" eyebrow="Procedencia visible" onClose={() => setSourceModal(false)}>
          <div className="source-list">
            {data.sources.map((source) => (
              <article key={source.id}>
                <StatusDot status={source.status} />
                <div><strong>{source.name}</strong><span>{source.authority} · {source.kind}</span></div>
                <span>
                  {source.age} · {source.status === "not_configured" ? "no configurada" : source.status}
                </span>
                <small>
                  {source.license}
                  {source.checksum ? ` · SHA-256 ${source.checksum.slice(0, 10)}…` : ""}
                  {source.records ? ` · ${source.records} registros` : ""}
                </small>
              </article>
            ))}
          </div>
          <div className="source-note">
            <ShieldCheck size={17} />
            <p>Los estados proceden de manifiestos de ingesta reales. Una fuente sin ejecución o credencial se muestra como tal; la telemetría SCADA y las imágenes siguen marcadas como sintéticas.</p>
          </div>
        </Modal>
      ) : null}

      {definitionId ? (
        <Modal title={definitionId.replaceAll("_", " ")} eyebrow="Definición de métrica" onClose={() => setDefinitionId(null)}>
          <p className="definition-copy">{data.definitions[definitionId] ?? "Definición registrada en metrics.yaml."}</p>
          <div className="definition-meta"><span>Owner</span><strong>Operations Analytics</strong><span>Grain</span><strong>asset · hour</strong><span>Freshness</span><strong>PT15M</strong></div>
        </Modal>
      ) : null}

      {noticeOpen ? (
        <Modal title="Actividad reciente" eyebrow="Centro de avisos" onClose={() => setNoticeOpen(false)}>
          <div className="notice-list">
            <article><Badge tone="warning">review</Badge><div><strong>Challenger eólico retenido</strong><span>Falta evidencia en régimen de viento extremo.</span></div></article>
            <article><Badge tone="success">passed</Badge><div><strong>Snapshot saneado publicado</strong><span>{data.quality_summary.checks_passed} de {data.quality_summary.checks_executed} controles superados.</span></div></article>
            <article><Badge tone="info">info</Badge><div><strong>Comando rápido</strong><span>La búsqueda global estará conectada en el perfil autenticado.</span></div></article>
          </div>
        </Modal>
      ) : null}
    </div>
  );
}

function Modal({
  title,
  eyebrow,
  children,
  onClose,
}: {
  title: string;
  eyebrow: string;
  children: React.ReactNode;
  onClose: () => void;
}) {
  return (
    <div className="modal-layer" role="dialog" aria-modal="true" aria-label={title}>
      <button type="button" className="modal-backdrop" onClick={onClose} aria-label="Cerrar modal" />
      <section className="modal-card">
        <header>
          <div><p className="eyebrow">{eyebrow}</p><h2>{title}</h2></div>
          <button type="button" className="icon-button" onClick={onClose} aria-label="Cerrar"><X size={17} /></button>
        </header>
        {children}
      </section>
    </div>
  );
}
