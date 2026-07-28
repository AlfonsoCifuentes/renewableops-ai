# System Card — RenewableOps AI

## Identity

- Version: 1.0.0
- Owner: Operations Analytics
- Review date: 2026-07-28
- Classification: public portfolio demonstration

## Purpose

Unificar telemetría, contexto meteorológico/mercado, forecasting, detección de
anomalías e inspección visual para priorizar revisión humana.

## System boundary

El sistema lee datos, calcula evidencia y publica recomendaciones. No dispone
de credenciales ni actuadores para PLC/SCADA, no envía consignas, no ejecuta
trading y no aprueba mantenimiento.

## Data

SCADA, fallos, imágenes de benchmark y portfolio son sintéticos/ficticios. Las
llamadas reales a REData/PVGIS son pequeñas, con procedencia, fecha y checksum.
No se requiere información personal.

## Models

Forecasting sklearn por tecnología, anomalías multicapa y visión clásica
calibrada. La validación es temporal; los intervalos son empíricos. El registry
exige aliases, gates y aprobación.

## Human oversight

El operador revisa contexto, evidencia, impacto y limitaciones antes de actuar.
Las incidencias incluyen una recomendación y nunca una orden automática.

## Monitoring

Freshness, missingness, duplicados, cuarentena, nMAE, bias, coverage, drift,
latencia, errores, snapshot age y MWh at risk. Prometheus/Grafana/Loki cubren la
capa local; Lakeflow/Unity Catalog cubren Databricks.

## Failure modes

Source outage, sensor congelado, cambio de régimen, forecast fuera de rango,
imagen corrupta/adversarial, modelo no disponible, snapshot obsoleto y
credencial expirada. Los fallbacks conservan el último dato válido y degradan
el estado de forma visible.

## Security and privacy

Uploads limitados y decodificados, snapshots saneados, secretos por entorno,
servicios loopback, RBAC/managed identity en nube, audit hash chain e incident
playbooks. Public demo no equivale a diseño productivo autenticado.

## Limitations

No existe validación en una planta real, el benchmark visual usa texturas
sintéticas y la optimización de batería es heurística. AI Act/NIS2/GDPR son un
mapeo de ingeniería, no certificación ni asesoramiento.

## Approval

Release local aprobada para demo. Despliegues remotos y promoción de un modelo
operativo requieren aprobación independiente del propietario.
