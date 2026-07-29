# Datos de demostración

`lakehouse/` contiene el seed reproducible que permite abrir el producto sin
red: Bronze conserva SCADA sintético; Silver normaliza y valida; Gold contiene
el holdout de forecasting. Los 12 activos y toda su telemetría son ficticios.
`lakehouse/bronze/official/` conserva las extracciones reales, pequeñas y
versionadas de REData, PVGIS y Eurostat. El perfil ignorado `scale/` puede
regenerar 2.522.928 filas a cinco minutos con `make scale-data`.

`manifests/` fija versión, fuentes, rango UTC, filas, hash de schema, SHA-256 de
contenido y flag sintético. `source_registry.yaml` es el catálogo de fuentes
oficiales, autenticación, atribución, revisión y fallback. Los snapshots
saneados publicados al navegador viven en `apps/dashboard/public/data`.

No añadir secretos, payloads personales ni datos de una planta real. Los
ficheros MLflow/SQLite y el audit log generado son estado local y no forman
parte del seed distribuible.
