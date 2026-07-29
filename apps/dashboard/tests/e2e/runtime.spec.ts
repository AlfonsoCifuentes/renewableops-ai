import { expect, test } from "@playwright/test";

test.describe("live local platform", () => {
  test.skip(process.env.RUNTIME_E2E !== "1", "requires Docker core profile");

  test("scenario travels from UI to FastAPI and persists audit evidence", async ({ page }) => {
    await page.goto("/scenario-lab");
    await page.getByRole("button", { name: /Ejecutar en sandbox/ }).click();
    await expect(page.getByRole("heading", { name: "Escenario detectado y revertido" })).toBeVisible();
    await expect(page.getByText("ejecución API auditada")).toBeVisible();
    await expect(page.getByText("sandbox limpio")).toBeVisible();
  });

  test("inspection inference and human review traverse the live API", async ({ page }) => {
    await page.goto("/inspections");
    const evidenceImage = await page.locator(".topbar").screenshot();
    const chooserPromise = page.waitForEvent("filechooser");
    await page.getByRole("button", { name: "Analizar imagen" }).click();
    const chooser = await chooserPromise;
    await chooser.setFiles({
      name: "runtime-evidence.png",
      mimeType: "image/png",
      buffer: evidenceImage,
    });
    await expect(page.locator(".upload-success")).toBeVisible({ timeout: 20_000 });
    await page.getByRole("button", { name: "Aprobar revisión" }).click();
    await expect(page.getByText(/Aprobada · auditoría/)).toBeVisible();
  });

  test("observability snapshot contains six evidenced workflow runs", async ({ page }) => {
    await page.goto("/observability");
    await expect(page.getByText("1 ejecución con evidencia", { exact: false })).toHaveCount(6);
    await expect(page.getByText(/configurado · no ejecutado/)).toHaveCount(0);
    await expect(page.getByText(/ms/).first()).toBeVisible();
  });
});
