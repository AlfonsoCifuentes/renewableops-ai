# RenewableOps AI 1.0.0

Release de portfolio reproducible, fechada el 2026-07-28.

Incluye lakehouse y modelos versionados, API, dashboard, seis automatizaciones,
observabilidad, gobierno, snapshots, PySpark/Databricks, Kubernetes/Helm y
Terraform Azure de referencia. Los schedules cloud están pausados y Terraform
no se aplica por defecto.

## Calidad de release

- Forecast solar/eólico supera persistencia en holdout temporal.
- Suite Python/API/Spark, UI y ocho E2E desktop/móvil aprobados.
- TypeScript estricto, ESLint, Ruff, build de producción y auditorías aprobados.
- Axe: cero violaciones en las dos vistas verificadas.
- Docker core/monitoring arrancado con healthchecks, scrape Prometheus,
  dashboard Grafana y ejecución n8n; Terraform, Kustomize, Helm y bundle
  Databricks validados.

La única evidencia pendiente es la ejecución en un workspace Databricks
propiedad del usuario. No afecta al núcleo local y está registrada en
`docs/issues/remote-databricks-validation.md`.

Consulta `docs/acceptance.md`, `CHANGELOG.md` y `docs/demo/demo-script.md` para
la trazabilidad completa.
