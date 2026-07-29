# Data Card — Official source samples

## Sources

REData (Red Eléctrica), PVGIS/JRC, Eurostat and AEMET OpenData are registered
with authority, URL, auth, attribution, cadence, fallback and last review.

## Collection

Requests are bounded, time-limited and retried with jitter. La extracción
verificada de 2026-07-29 guardó 32 registros REData, 228 PVGIS y 6 Eurostat,
con source/update timestamps, headers saneados, schema fingerprint y SHA-256.
Los payloads Bronze no se publican en el snapshot del navegador.

## Quality and limitations

External schemas, terms, availability and historic corrections can change.
Contract tests and registry review are required before expanding a window.
AEMET requires a user-provided key and therefore appears como `not_configured`.
A source failure is shown as fallback, never as successful official data.

## Privacy / usage

Public operational/environmental data only. Dataset-specific licenses and
attribution remain controlling.
