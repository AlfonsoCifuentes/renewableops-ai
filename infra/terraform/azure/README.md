# Azure reference architecture

This directory is an unapplied, cost-guarded reference. The default creates the
shared security foundation only; `enable_paid_reference = true` is required for
PostgreSQL, Event Hubs, Container Apps, Azure ML, and Azure Databricks.

```bash
terraform init -backend=false
terraform fmt -check -recursive
terraform validate
terraform plan -var-file=terraform.tfvars
```

For shared environments, copy the backend example to a secure out-of-band
configuration and use Entra authentication. Never commit state, plans,
credentials, or real contact addresses. Private endpoints, managed identity,
RBAC Key Vault, diagnostic export, mandatory tags, and a forecasted 80% budget
alert are part of the baseline.

`terraform plan` can still query Azure and should be run only in a subscription
where the operator is authorized. This repository never runs `apply`
automatically.
