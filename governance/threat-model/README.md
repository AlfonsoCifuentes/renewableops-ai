# Threat model

Método: STRIDE sobre flujos y límites de confianza.

| Amenaza | Superficie | Control | Residual |
|---|---|---|---|
| Spoofing | webhooks/API privada | OIDC/JWT y HMAC requeridos fuera de demo | medium |
| Tampering | manifests/audit | SHA-256, previous hash, immutable Bronze | low |
| Repudiation | promoción/incidente | actor, correlation ID, approval evidence | low |
| Information disclosure | snapshots/logs | allowlist de campos, redacción, no PII | low |
| Denial of service | upload/inferencia | 5 MB, 24 MP, bounded models, rate limit at gateway | medium |
| Elevation | containers/cloud | non-root, no token mount, RBAC, managed identity | low |
| Model evasion | imágenes | confianza, blur checks, revisión humana | medium |
| Data poisoning | sources/SCADA | provenance, schema, quarantine, drift gates | medium |

## Crown jewels

Secretos de fuente, modelos Champion, manifests, aliases, audit evidence y
snapshots publicados.

## Trust boundaries

Internet→ingesta; browser→API; upload→decoder/model; n8n→API; CI→registry;
Databricks workspace→Unity Catalog. Un entorno real debe añadir WAF/rate
limiting, private ingress, MFA/PAM, SIEM y pentest.
