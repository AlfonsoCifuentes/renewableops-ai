import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { DashboardApp } from "@/components/dashboard-app";
import { getDashboardData } from "@/lib/data";
import type { SectionId } from "@/lib/types";

const sections: SectionId[] = [
  "fleet",
  "forecast-solar",
  "forecast-wind",
  "market",
  "asset-health",
  "inspections",
  "data-explorer",
  "data-quality",
  "mlops",
  "observability",
  "governance",
  "scenario-lab",
];

const titles: Record<SectionId, string> = {
  overview: "Overview",
  fleet: "Fleet",
  "forecast-solar": "Forecast Solar",
  "forecast-wind": "Forecast Wind",
  market: "Market",
  "asset-health": "Asset Health",
  inspections: "Visual Inspections",
  "data-explorer": "Data Explorer",
  "data-quality": "Data Quality",
  mlops: "MLOps",
  observability: "Observability",
  governance: "Governance & Security",
  "scenario-lab": "Scenario Lab",
};

export function generateStaticParams() {
  return sections.map((section) => ({ section }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ section: string }>;
}): Promise<Metadata> {
  const { section } = await params;
  if (!sections.includes(section as SectionId)) return {};
  return { title: titles[section as SectionId] };
}

export default async function SectionPage({
  params,
}: {
  params: Promise<{ section: string }>;
}) {
  const { section } = await params;
  if (!sections.includes(section as SectionId)) notFound();
  const data = await getDashboardData();
  return (
    <Suspense fallback={<div className="boot-screen"><p>Cargando módulo…</p></div>}>
      <DashboardApp data={data} initialSection={section as SectionId} />
    </Suspense>
  );
}
