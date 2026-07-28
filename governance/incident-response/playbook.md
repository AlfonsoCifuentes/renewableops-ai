# Incident response

## Severidad

- SEV-1: riesgo de control físico, secreto expuesto o corrupción amplia.
- SEV-2: modelo/snapshot materialmente incorrecto o servicio crítico caído.
- SEV-3: degradación acotada con fallback.
- SEV-4: defecto menor sin impacto operativo.

## Flujo

1. Detectar y crear `correlation_id`.
2. Triage: alcance, dato/modelo/servicio, severidad y owner.
3. Contener: bloquear publicación, conservar snapshot válido, revocar secreto o
   volver Champion a Rollback.
4. Preservar logs, manifests, hashes, versión, actor y timestamps.
5. Erradicar causa y añadir test.
6. Recuperar gradualmente y verificar SLO/quality gates.
7. Comunicar hechos, incertidumbre y próximo update.
8. Postmortem sin culpa en 5 días laborables.

## Casos

### Secreto expuesto

Revocar primero, buscar uso, rotar dependencias, borrar exposición sin destruir
evidencia y revisar alcance. No pegar el valor en tickets o logs.

### Modelo degradado

Congelar promoción, cambiar a Rollback, comparar ventana/regímenes, validar
features y dataset hash, abrir aprobación nueva.

### Snapshot incorrecto

Retirar manifest, servir último histórico válido, registrar `SNAPSHOT_REVOKED`,
reconstruir desde inputs versionados y comunicar freshness.
