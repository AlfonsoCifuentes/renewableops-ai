import { expect, test } from "@playwright/test";

test("overview loads and supports global navigation", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "La cartera, en una sola lectura." })).toBeVisible();
  await expect(page.getByText("Datos válidos")).toBeAttached();
  if ((page.viewportSize()?.width ?? 1280) < 700) {
    await page.getByRole("button", { name: "Abrir navegación" }).click();
  }
  await page.getByRole("button", { name: "Fleet" }).click();
  await expect(page).toHaveURL(/\/fleet/);
  await expect(page.getByRole("heading", { name: "Flota renovable" })).toBeVisible();
});

test("filters are reflected in the URL and asset list", async ({ page }) => {
  await page.goto("/fleet");
  await expect(page.getByRole("heading", { name: "Flota renovable" })).toBeVisible();
  const mobileFilterToggle = page.getByRole("button", { name: /^Filtros/ });
  if ((page.viewportSize()?.width ?? 1280) < 700) {
    await mobileFilterToggle.click();
  }
  await page.getByLabel("Tecnología").selectOption("solar");
  await expect(page).toHaveURL(/technology=solar/);
  await expect(page.getByRole("heading", { name: "5 activos", exact: true })).toBeVisible();
});

test("scenario lab executes a deterministic sandbox run", async ({ page }) => {
  let submitted: Record<string, unknown> | null = null;
  await page.route("http://localhost:8000/api/v1/scenarios", async (route) => {
    submitted = route.request().postDataJSON() as Record<string, unknown>;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        run_id: "scn-e2e-audited",
        status: "completed",
        detected_by: "Residual + Isolation Forest",
        detection_seconds: 43,
        estimated_mwh_at_risk: 41.2,
        action: "Schedule thermographic inspection",
        audit_event_id: "AUD-E2E",
        reverted: true,
      }),
    });
  });
  await page.goto("/scenario-lab");
  await page.getByRole("button", { name: /Ejecutar en sandbox/ }).click();
  await expect(page.getByRole("heading", { name: "Escenario detectado y revertido" })).toBeVisible();
  await expect(page.getByText("sandbox limpio")).toBeVisible();
  await expect(page.getByText("ejecución API auditada")).toBeVisible();
  expect(submitted).toMatchObject({
    scenario: "soiling",
    asset_id: "sol-cmn-01",
    severity: 62,
    duration_hours: 12,
    seed: 42,
  });
});

test("scenario lab labels the offline preview without claiming execution", async ({ page }) => {
  await page.route("http://localhost:8000/api/v1/scenarios", (route) => route.abort());
  await page.goto("/scenario-lab");
  await page.getByRole("button", { name: /Ejecutar en sandbox/ }).click();
  await expect(page.getByRole("heading", { name: "Vista previa determinista" })).toBeVisible();
  await expect(page.getByText("modo offline", { exact: true })).toBeVisible();
  await expect(page.getByText("sin ejecución ni auditoría")).toBeVisible();
  await expect(page.getByText("No aplicado en modo offline")).toBeVisible();
});

test("mobile navigation remains usable", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByRole("button", { name: "Abrir navegación" }).click();
  await page.getByRole("button", { name: "MLOps" }).click();
  await expect(page).toHaveURL(/\/mlops/);
  await expect(page.getByRole("heading", { name: "Modelos con criterio de promoción." })).toBeVisible();
});

test("source provenance exposes only verified evidence", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Fuentes" }).click();
  const dialog = page.getByRole("dialog", { name: "Fuentes y freshness" });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByText("REData API")).toBeVisible();
  await expect(dialog.getByText("PVGIS API")).toBeVisible();
  await expect(dialog.getByText("Eurostat renewable energy indicators")).toBeVisible();
  await expect(dialog.getByText("AEMET OpenData")).toBeVisible();
  await expect(dialog.getByText(/AEMET.*no configurada/i)).toBeVisible();
});

test("asset drill-down opens and closes as an accessible dialog", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /Lumen La Mancha/ }).focus();
  await page.keyboard.press("Enter");
  const drawer = page.getByRole("dialog", { name: "Detalle de Lumen La Mancha" });
  await expect(drawer).toBeVisible();
  await expect(drawer.getByText("Modelo")).toBeVisible();
  await drawer.getByRole("button", { name: "Cerrar", exact: true }).click();
  await expect(drawer).toBeHidden();
});

test("forecast export produces a 48-hour CSV", async ({ page }) => {
  await page.goto("/forecast-solar");
  await expect(page.getByRole("heading", { name: /Lo que producirá la cartera/ })).toBeVisible();
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Descargar previsión" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/^forecast-(solar|wind)-48h\.csv$/);
});

test("inspection upload traverses the documented API boundary", async ({ page }) => {
  await page.route("http://localhost:8000/api/v1/inspections", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        status: "completed",
        prediction: "defective",
        confidence: 0.91,
      }),
    });
  });
  await page.goto("/inspections");
  const fileChooserPromise = page.waitForEvent("filechooser");
  await page.getByRole("button", { name: "Analizar imagen" }).click();
  const fileChooser = await fileChooserPromise;
  await fileChooser.setFiles({
    name: "cell.png",
    mimeType: "image/png",
    buffer: Buffer.from(
      "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
      "base64",
    ),
  });
  await expect(page.getByText("defective · 91%")).toBeVisible({ timeout: 10_000 });
});

test("governance reports evidence instead of certification scores", async ({ page }) => {
  await page.goto("/governance");
  await expect(page.getByRole("heading", { name: "Controles, límites y evidencia." })).toBeVisible();
  await expect(page.getByText("SBOM")).toBeVisible();
  await expect(page.getByText("2 artefactos · CycloneDX inventory")).toBeVisible();
  await expect(page.getByText("Mapeado").first()).toBeVisible();
  await expect(page.getByText(/not legal advice/i)).toBeVisible();
  await expect(page.getByText("12/12")).toHaveCount(0);
});

test("model page exposes temporal selection, drift, and pending approval", async ({ page }) => {
  await page.goto("/mlops");
  await expect(page.getByText(/3 folds temporales · gap 24 h/).first()).toBeVisible();
  await expect(page.getByText("Pending manual approval").first()).toBeVisible();
  await expect(page.getByText("Drift PSI").first()).toBeVisible();
  await expect(page.getByRole("button", { name: "No desplegado" }).first()).toBeDisabled();
});
