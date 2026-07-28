# Evaluación de ingeniería — EU AI Act

La demo es un sistema analítico de apoyo, sin control de infraestructura crítica
y sin decisiones sobre personas. Con este alcance no se afirma una
clasificación legal definitiva.

Controles inspirados en el marco:

| Área | Evidencia |
|---|---|
| Gestión de riesgos | `risk-register.csv`, gates y playbooks |
| Gobierno de datos | contratos, registry, manifests, synthetic flags |
| Documentación técnica | system/model/data cards y ADR |
| Logging | correlación, MLflow y audit hash chain |
| Transparencia | provenance, intervalos y límites visibles |
| Supervisión humana | promoción y acciones requieren aprobación |
| Robustez/ciberseguridad | tests, upload limits, rollback, monitoring |

Un uso real dentro de infraestructura energética exigiría análisis jurídico,
clasificación, calidad de datos representativa, gestión de proveedores,
evaluación de conformidad y vigilancia post-market adicionales.
