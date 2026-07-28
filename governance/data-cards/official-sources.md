# Data Card — Official source samples

## Sources

REData (Red Eléctrica), AEMET OpenData and PVGIS/JRC are registered with
authority, URL, auth, attribution, cadence, fallback and last review.

## Collection

Requests are bounded, time-limited and retried with jitter. Payload evidence
includes source ID, extraction timestamp, status and SHA-256. Raw payloads are
not published in the browser snapshot.

## Quality and limitations

External schemas, terms, availability and historic corrections can change.
Contract tests and registry review are required before expanding a window.
AEMET requires a user-provided key. A source failure is shown as fallback, not
reported as successful official data.

## Privacy / usage

Public operational/environmental data only. Dataset-specific licenses and
attribution remain controlling.
