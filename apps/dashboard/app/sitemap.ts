import type { MetadataRoute } from "next";

const routes = [
  "",
  "/fleet",
  "/forecast-solar",
  "/forecast-wind",
  "/market",
  "/asset-health",
  "/inspections",
  "/data-explorer",
  "/data-quality",
  "/mlops",
  "/observability",
  "/governance",
  "/scenario-lab",
];

export default function sitemap(): MetadataRoute.Sitemap {
  const base = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";
  return routes.map((route) => ({
    url: `${base}${route}`,
    changeFrequency: "daily",
    priority: route === "" ? 1 : 0.8,
  }));
}
