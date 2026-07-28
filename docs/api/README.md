# API

Base local: `http://localhost:8000/api/v1`. El contrato navegable vive en
`/docs`.

Endpoints:

- `GET /overview`, `/assets`, `/anomalies`, `/models`
- `POST /forecast`
- `POST /scenarios`
- `POST /inspections`
- `POST /battery/dispatch`
- `GET /health/live`, `/health/ready`, `/metrics`

Las escrituras de escenario son simulaciones idempotentes por escenario,
activo y seed. Los uploads aceptan PNG/JPEG/WebP, máximo 5 MB y 24 MP. Los
errores de validación no devuelven stack traces. `X-Correlation-ID` viaja en
cada respuesta.

En `PUBLIC_DEMO=true` las lecturas saneadas son públicas. Un despliegue real
debe poner la API tras OIDC/JWT, gateway con rate limiting y TLS; no basta con
CORS.
