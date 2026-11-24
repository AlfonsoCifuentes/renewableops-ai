import { cache } from "react";
import { z } from "zod";

import type { DashboardSnapshot } from "@/lib/types";
// Importado en el bundle (antes fs.readFile): Cloudflare Workers no tiene
// sistema de archivos. El fichero sigue publicándose en /data/latest/.
import snapshot from "../public/data/latest/dashboard.json";

const metaSchema = z.object({
  snapshot_version: z.string(),
  generated_at: z.string(),
  data_through: z.string(),
  display_timezone: z.string(),
  pipeline_run_id: z.string(),
  data_status: z.string(),
  is_demo: z.boolean(),
  contains_synthetic_data: z.boolean(),
  source_note: z.string(),
});

const snapshotBoundary = z
  .object({
    meta: metaSchema,
    kpis: z.object({
      forecast_24h_mwh: z.number(),
      assets_online: z.number(),
      assets_total: z.number(),
      active_anomalies: z.number(),
      mwh_at_risk: z.number(),
      revenue_7d_eur: z.number(),
      forecast_nmae: z.number(),
      availability: z.number(),
      data_freshness_minutes: z.number(),
    }),
    assets: z.array(z.object({ asset_id: z.string(), name: z.string() }).passthrough()),
    series: z.array(z.object({ timestamp: z.string() }).passthrough()),
  })
  .passthrough();

export const getDashboardData = cache(async (): Promise<DashboardSnapshot> => {
  const parsed: unknown = snapshot;
  snapshotBoundary.parse(parsed);
  return parsed as DashboardSnapshot;
});
