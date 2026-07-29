# Estado de aceptación

Fecha de corte: 2026-07-29. Release: 1.0.0.

Esta matriz responde literalmente a las 31 preguntas finales de la
especificación. Un «sí» exige código ejecutado y evidencia versionada; un
recurso cloud declarado pero no ejecutado no cuenta como ejecución remota.

| # | Estado | Evidencia |
|---:|:---:|---|
| 1 | Sí | Bootstrap Windows/Linux, `uv.lock`, `package-lock.json`, seed y arranque local verificados. |
| 2 | Sí | Seed de 25.920 filas y perfil de escala de 2.522.928 filas, 12 activos, 730 días, cinco minutos y 20 escenarios; hashes válidos en `artifacts/verification/scada-scale.json`. |
| 3 | Sí | Ejecución real `ingest-20260729T093102Z-8de154f4`: REData 32, PVGIS 228 y Eurostat 6 registros; AEMET se declara `not_configured` sin clave. |
| 4 | Sí | Registry, data cards, seis manifests de dataset, schema fingerprints, timestamps y SHA-256. |
| 5 | Sí | Pandas normaliza UTC, deduplica, valida reglas físicas y escribe Bronze/Silver/Gold; reconciliación Spark independiente aprobada. |
| 6 | Sí | NumPy genera señales físicas y 20 fallos, cuantifica anomalías, calcula batería y alimenta PSI/estadística visual. |
| 7 | Sí | Ridge, ElasticNet, RandomForest, ExtraTrees e HistGradientBoosting se entrenan por tecnología. |
| 8 | Sí | Lags 1/24/168 h y rolling desplazado; TimeSeriesSplit de 3 folds, gap 24 h y test final de 14 días intacto. |
| 9 | Sí | Cinco baselines: 1 h, 24 h, 168 h, hora/día y referencia física; skill registrado. |
| 10 | Sí | Tres regresores cuantílicos entrenados para P10/P50/P90; pinball, cobertura, nRMSE, anchura y reparación de cruces documentados. |
| 11 | Sí | Reglas físicas, residuos e Isolation Forest con severidad, causa, recomendación y MWh/€ en riesgo. |
| 12 | Sí | ELPV real: 2.624 imágenes, HOG/LBP/textura, cinco candidatos, calibración, test de 525 imágenes y slices mono/poly. |
| 13 | Sí | MLflow local SQLite recibió los diez candidatos de la pasada final, métricas, parámetros, manifest, signature, input example y champions. |
| 14 | Sí | Registry Champion/Challenger, selección por validación, gates y rollback. Los champions de demo están aprobados mediante recibos ligados al SHA-256; cada reentrenamiento invalida la aprobación y no hay autopromoción. |
| 15 | Sí | Nueve servicios Docker; healthchecks, Prometheus targets `up`, dashboard Grafana provisionado y Loki operativo. |
| 16 | Sí | Next.js con 13 áreas, URL state, filtros, drill-down, CSV, responsive, tema dual y estados de carga/error/vacío. |
| 17 | Sí | Seis workflows n8n importados y ejecutados con éxito; duración individual en `artifacts/verification/n8n-executions.json`. |
| 18 | Sí | Snapshot saneado, manifest SHA-256, histórico diario, comando publish sin reentrenar y workflow GitHub programado. |
| 19 | Sí | Threat model, CSP/headers, MIME/bytes/píxeles, CORS acotado, auditoría, SBOM CycloneDX, Bandit, escaneo de secretos, pip-audit y npm audit. |
| 20 | Sí | System/model/data cards, intended/prohibited use, AI Act/NIS2/NIST/GDPR, riesgos y aprobación humana. |
| 21 | Sí | Playbook SEV-1–4 y Scenario Lab real; el E2E live persiste el evento y comprueba reversión del sandbox. |
| 22 | Sí | Alias Rollback, runbook y estrategia Kubernetes canary/rollback; producción sigue no desplegada. |
| 23 | Sí | Terraform 1.15.8: `fmt -check` y `validate` pasan sin `plan/apply`. |
| 24 | Sí | Databricks CLI 1.9.0: bundle, interpolación y schema pasan en modo estricto y offline. |
| 25 | No — externo | Lakeflow está implementado, pero un run remoto requiere workspace OAuth del propietario. |
| 26 | No — externo | Jobs diarios/semanales están implementados, pero no se atribuye una ejecución remota inexistente. |
| 27 | Sí, con límite | Registry local/MLflow funciona; Unity Catalog Model Registry está implementado y la ausencia de ejecución remota está documentada. |
| 28 | No — externo | AI/BI `.lvdash.json` y recurso bundle validan; publicar exige una cuenta Databricks autorizada. |
| 29 | Sí | Pandas/PySpark 4.2 reconcilian agregados horarios con JDK 25 en test de integración. |
| 30 | Sí | 45 Python/API/model + 1 Spark + 6 UI + 22 E2E responsive + 3 E2E live; lint, tipos, build, seguridad y runtime pasan. |
| 31 | Sí | UI, manifests y documentación distinguen dato oficial, sintético, derivado, evaluación, simulación y recurso no desplegado. |

## Resultado medido

- Forecast seleccionado por validación: solar RandomForest, MAE test 0,8883 MW,
  nMAE 1,68 %, skill 65,97 % y cobertura P10–P90 95,01 %; eólico ExtraTrees,
  MAE 2,6610 MW, nMAE 3,766 %, skill 84,50 % y cobertura 83,68 %.
- Visión ELPV: balanced accuracy 0,7337, macro F1 0,7467, PR-AUC 0,7354 y
  ROC-AUC 0,8254. Es evidencia de benchmark, no validación de planta.
- Runtime: API 46,09 ms, dashboard 6,39 ms, n8n 3,05 ms, Grafana 1,86 ms y
  Prometheus 12,54 ms en la sonda local final; los nueve servicios requeridos
  estaban operativos.
- Calidad: Ruff, Mypy sobre 24 módulos, ESLint, TypeScript y build Next.js
  pasan. Pytest: 43 aprobadas, incluida la reconciliación Spark al declarar el
  JDK compatible. Playwright: 22 responsive y 3 live aprobadas.
- Seguridad: pip-audit y Bandit no encuentran vulnerabilidades/hallazgos altos;
  npm no encuentra críticas. Las 12 altas del árbol completo —tres en runtime—
  tienen exposición y salida documentadas en
  `governance/security-exceptions.md`.

## Único gate externo

Los puntos 25, 26 y 28 comparten una sola dependencia externa: el propietario
debe autenticar su Databricks Free Edition mediante OAuth. El código, bundle y
validación estructural están terminados; no es legítimo crear una cuenta,
aceptar términos o publicar en un workspace ajeno. El procedimiento exacto está
en `docs/issues/remote-databricks-validation.md`.
