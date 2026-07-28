import { Suspense } from "react";

import { DashboardApp } from "@/components/dashboard-app";
import { getDashboardData } from "@/lib/data";

export default async function HomePage() {
  const data = await getDashboardData();
  return (
    <Suspense fallback={<DashboardSkeleton />}>
      <DashboardApp data={data} initialSection="overview" />
    </Suspense>
  );
}

function DashboardSkeleton() {
  return (
    <main className="boot-screen">
      <div className="boot-mark" />
      <p>Preparando el control room…</p>
    </main>
  );
}
