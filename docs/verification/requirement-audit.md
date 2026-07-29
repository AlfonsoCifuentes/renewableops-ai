# Auditoría de cumplimiento de la especificación maestra

Fecha: 2026-07-29. Alcance: repositorio local, datos versionados, perfiles
Docker y validación estructural de capas cloud.

## Método

Cada claim visible se rastreó hasta una de estas evidencias:

1. artefacto con checksum o métrica calculada;
2. test automatizado;
3. ejecución live contra la plataforma Docker;
4. definición estructural validada, marcada expresamente como no desplegada.

No se contabilizaron ficheros declarativos como ejecuciones remotas. Las
credenciales, rutas locales y payloads Bronze se excluyeron del snapshot
público.

## Evidencia principal

| Dominio | Evidencia ejecutada |
|---|---|
| Fuentes | `data/manifests/source_status.json` y tres manifests oficiales |
| Escala | `artifacts/verification/scada-scale.json` |
| Forecast | `data/models/*_forecast_evidence.json`, métricas y artefactos |
| Visión | `data/models/cv_metrics.json` y champion ELPV |
| Drift | `data/models/drift_metrics.json` |
| MLOps | `data/mlflow.db` y `data/models/model_registry.json` |
| n8n | `artifacts/verification/n8n-executions.json` |
| Runtime | `artifacts/verification/container-runtime.json` |
| Seguridad | pip-audit, npm audit, Bandit, secret scan y dos SBOM CycloneDX |
| Plataforma | `artifacts/verification/platform-validation.json` |
| Aceptación | `docs/acceptance.md` |

## Correcciones de profundidad realizadas

- La ingesta pasó de conectores ornamentales a ejecuciones reales con raw
  Bronze, headers saneados, timestamps, schema fingerprint y checksum.
- El perfil big-data pasó a más de 2,5 millones de filas particionadas con 20
  escenarios reproducibles.
- La selección de forecast dejó el test fuera del ranking, añadió cinco
  candidatos, cinco baselines, cuantiles entrenados, inferencia recursiva 48 h
  y MAE real por horizonte.
- La visión sintética se sustituyó por ELPV real, con licencia, annotation hash,
  cinco candidatos, calibración, test intacto y métricas por tipo de célula.
- Los seis workflows n8n se importaron y ejecutaron; el dashboard muestra esa
  evidencia en vez de estados inventados.
- Scenario Lab, inferencia visual y revisión humana se probaron desde navegador
  hasta FastAPI y auditoría.
- Gobierno, uptime, compliance y aprobación se reescribieron para mostrar
  evidencia y límites, nunca certificaciones o despliegues inexistentes.

## Límites explícitos

- El portfolio y SCADA son sintéticos; no demuestran generalización industrial.
- ELPV es no comercial y no sustituye inspección técnica.
- AEMET requiere una clave del propietario y se mantiene `not_configured`.
- Lakeflow, Jobs y AI/BI remotos requieren OAuth de un workspace Databricks del
  propietario. La ausencia de esa ejecución permanece visible en toda la demo.
