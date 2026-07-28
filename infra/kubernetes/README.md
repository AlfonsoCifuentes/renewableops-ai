# Local Kubernetes reference

Validate without applying:

```bash
kubectl kustomize infra/kubernetes
kubectl apply --dry-run=client -k infra/kubernetes
```

Images are intentionally immutable release tags. Supply the example secret
through a proper secret workflow before applying. The canary manifest is an
explicit opt-in example and is not part of `kustomization.yaml`.

Rollback drill:

```bash
kubectl set image deployment/renewableops-api api=renewableops-api:1.0.1
kubectl rollout status deployment/renewableops-api
kubectl rollout undo deployment/renewableops-api
```
