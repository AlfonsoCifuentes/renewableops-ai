# Estado de aceptación

Fecha de corte: 2026-07-28. Release: 1.0.0.

Esta matriz responde literalmente a las 31 preguntas de la especificación. Una
respuesta «sí» exige código y evidencia local; la existencia de un fichero cloud
no se presenta como una ejecución remota.

| # | Estado | Evidencia |
|---:|:---:|---|
| 1 | Sí | `scripts/bootstrap.ps1`, `scripts/bootstrap.sh`, lockfiles y arranque local verificado. |
| 2 | Sí | 25.920 filas / 12 activos en `data/lakehouse`; el seed es determinista. |
| 3 | Sí | Clientes HTTP reales y acotados para REData, PVGIS y AEMET; PVGIS respondió con checksum. REData devolvió HTTP 400 y AEMET exige clave, ambos declarados como fallback. |
| 4 | Sí | `data/source_registry.yaml`, data cards y tres manifiestos SHA-256. |
| 5 | Sí | `pipeline.py` normaliza, interpola, deduplica y escribe Bronze/Silver/Gold con Pandas. |
| 6 | Sí | NumPy genera señales físicas, fallos, cuantiles, residuals, optimización de batería y visión sintética. |
| 7 | Sí | Ridge, ExtraTrees e HistGradientBoosting se entrenan para solar y eólica. |
| 8 | Sí | Lags/rollings causales con `shift(1)` y holdout final bloqueado de 14 días. |
| 9 | Sí | Persistencia de 24 h; tests exigen skill positivo. |
| 10 | Sí | P10/P50/P90 ordenados y cobertura registrada. |
| 11 | Sí | Reglas físicas, residuales e Isolation Forest con severidad e impacto. |
| 12 | Sí | HOG + LBP + LogisticRegression calibrada y artefacto versionado. |
| 13 | Sí | MLflow 3 local sobre SQLite: doce ejecuciones candidatas verificadas. |
| 14 | Sí | Registry Champion/Challenger, gates, aprobación manual y alias de rollback. |
| 15 | Sí | Prometheus scrapeó la API como `up`; Grafana provisionó el dashboard y Loki arrancó en el perfil real. |
| 16 | Sí | Next.js: 13 áreas, URL state, filtros, escenarios, drill-down, CSV, responsive y tema dual. |
| 17 | Sí | Seis workflows n8n importables; una ejecución CLI real terminó en `success`. |
| 18 | Sí | Snapshot saneado y manifiesto público; workflow programado de publicación. |
| 19 | Sí | Threat model, CSP, headers, límites, MIME/decode, HMAC, auditoría y scans. |
| 20 | Sí | System/model/data cards, matriz legal, riesgos y aprobación humana. |
| 21 | Sí | Playbook SEV-1–4 y Scenario Lab con detección, contención y reversión. |
| 22 | Sí | Alias Rollback, runbook y estrategia Kubernetes canary/rollback. |
| 23 | Sí | Terraform 1.15.8: `fmt -check` y `validate` pasan sin aplicar recursos. |
| 24 | Sí | Databricks CLI 1.9.0: interpolación y schema del bundle pasan en modo estricto. |
| 25 | No — externo | Lakeflow está implementado, pero no se inventa un run sin workspace autenticado. |
| 26 | No — externo | Los Jobs y dependencias están implementados, pero falta un run remoto autorizado. |
| 27 | Sí, con límite | Registry local funciona; el registro en Unity Catalog está implementado y su falta de ejecución remota está documentada. |
| 28 | No — externo | El `.lvdash.json` y el recurso AI/BI validan, pero no hay publicación en una cuenta ajena. |
| 29 | Sí | Reconciliación Pandas/PySpark 4.2 ejecutada con Temurin 21 y test aprobatorio. |
| 30 | Sí | Python/API/Spark, frontend, E2E desktop/mobile, lint, tipos, build y seguridad pasan. |
| 31 | Sí | Cada pantalla y artefacto distingue oficial, derivado, sintético, simulación y referencia no desplegada. |

## Resultado medido

- Forecast campeón: solar MAE 1,0188 MW y skill 0,6097; eólico MAE
  2,8901 MW y skill 0,8317.
- API: test P95 local inferior a 250 ms; navegador observado con FCP/LCP de
  aproximadamente 272 ms y CLS 0.
- Accesibilidad: cero violaciones Axe en desktop y móvil; ocho escenarios E2E
  pasan en Chromium desktop/móvil.
- Tests: 26 pruebas Python/API/Spark, tres pruebas de componentes y ocho
  escenarios E2E aprobados; Mypy valida 20 módulos fuente.
- Seguridad: `pip-audit` sin vulnerabilidades conocidas y auditoría npm sin
  críticas; los avisos no corregibles están razonados en
  `governance/security-exceptions.md`.
- Plataforma: los perfiles Docker core/monitoring arrancan y pasan endpoints;
  Terraform, Kustomize, Helm y schema del bundle también pasan. Véanse los JSON
  de `artifacts/verification/`.

## Gates externos abiertos

Los puntos 25, 26 y 28 son una única dependencia externa: el propietario debe
autenticar un Databricks Free Edition propio. El registro completo con bloqueo,
impacto, alternativa y siguiente paso está en
`docs/issues/remote-databricks-validation.md`. No requiere cambios de código.
