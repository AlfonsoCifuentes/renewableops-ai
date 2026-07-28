# Runbook local

## Pipeline

```bash
uv run renewableops run-demo --days 90
uv run python scripts/verify_environment.py
```

Una ejecución correcta crea Parquet Bronze/Silver/Gold, tres manifiestos,
modelos joblib, registry, audit JSONL y snapshot público.

## Recuperación

1. Detener nuevos runs.
2. Conservar `data/manifests` y `data/audit/events.jsonl`.
3. Verificar el último snapshot por `content_hash`.
4. Servir `apps/dashboard/public/data/history/<fecha>`.
5. Reproducir con la semilla y ventana registradas.
6. Comparar recuentos y hashes antes de republicar.

## Source outage

No borrar el último snapshot válido. Registrar freshness degradada, activar el
fallback declarado y reintentar con jitter. Nunca etiquetar un fallback como
fuente oficial.

## Modelo degradado

Congelar promociones, volver el alias Champion a Rollback, validar latencia y
nMAE, y abrir revisión humana. El serving conserva el modelo anterior.
