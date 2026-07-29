# RenewableOps AI 1.0.0

Release de portfolio reproducible, auditada el 2026-07-29.

Incluye lakehouse y modelos versionados, API, dashboard, seis automatizaciones,
observabilidad, gobierno, snapshots, PySpark/Databricks, Kubernetes/Helm y
Terraform Azure de referencia. Los schedules cloud están pausados y Terraform
no se aplica por defecto.

## Calidad de release

- Forecast solar/eólico supera persistencia en holdout temporal.
- 42 pruebas Python/API, reconciliación Spark, tres pruebas UI,
  22 E2E desktop/móvil y tres E2E live contra Docker aprobados.
- TypeScript estricto, ESLint, Ruff, build de producción y auditorías aprobados.
- Docker core/monitoring arrancado con healthchecks, scrape Prometheus,
  dashboard Grafana y seis ejecuciones n8n; Terraform, Kustomize, Helm y bundle
  Databricks validados.
- REData, PVGIS y Eurostat ingeridos realmente; perfil de escala de 2.522.928
  filas y benchmark ELPV de 2.624 imágenes verificados.

La única evidencia pendiente es la ejecución en un workspace Databricks
propiedad del usuario. No afecta al núcleo local y está registrada en
`docs/issues/remote-databricks-validation.md`.

Consulta `docs/acceptance.md`, `CHANGELOG.md` y `docs/demo/demo-script.md` para
la trazabilidad completa.
