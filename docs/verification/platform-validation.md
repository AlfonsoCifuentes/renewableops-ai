# Validación de plataforma

Ejecución local del 2026-07-29:

| Capa | Herramienta | Resultado |
|---|---|---|
| Compose | Docker CLI 29.6.2 | `docker compose config --quiet` pasa. |
| Azure IaC | Terraform 1.15.8 | formato y validación pasan; no se ejecutó `plan/apply`. |
| Kubernetes | kubectl 1.36.2 / Kustomize 5.8.1 | render completo válido. |
| Helm | 4.2.2 | lint estricto y template pasan. |
| Databricks | CLI 1.9.0 | schema/interpolación del bundle pasan en estricto. |
| Spark | PySpark 4.2 / JDK 25 | reconciliación con Pandas pasa. |

Además de la validación declarativa, se levantaron los perfiles `core` y
`monitoring` con Docker Desktop 4.83.0 / Engine 29.6.2. API, dashboard, MinIO,
PostgreSQL y MLflow quedaron healthy; n8n, Grafana, Prometheus y Loki quedaron
running. Los endpoints de API, dashboard, n8n, Grafana y Prometheus respondieron
200, Prometheus scrapeó la API como `up`, Grafana provisionó el dashboard y los
seis workflows n8n importados terminaron con estado `success`. Tres pruebas
live recorrieron navegador → FastAPI → modelos/auditoría y navegador →
snapshot de observabilidad.

El JSON reproducible se genera con `scripts/validate_platform.py`; acepta rutas
explícitas a cada CLI y nunca despliega ni aplica infraestructura.
La evidencia viva está en `artifacts/verification/container-runtime.json`. Los
contenedores se detienen después de la verificación para no consumir recursos.
