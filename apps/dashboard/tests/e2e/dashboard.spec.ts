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
  await page.goto("/scenario-lab");
  await page.getByRole("button", { name: /Ejecutar en sandbox/ }).click();
  await expect(page.getByRole("heading", { name: "Escenario detectado y revertido" })).toBeVisible();
  await expect(page.getByText("sandbox limpio")).toBeVisible();
});

test("mobile navigation remains usable", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByRole("button", { name: "Abrir navegación" }).click();
  await page.getByRole("button", { name: "MLOps" }).click();
  await expect(page).toHaveURL(/\/mlops/);
  await expect(page.getByRole("heading", { name: "Modelos con criterio de promoción." })).toBeVisible();
});
