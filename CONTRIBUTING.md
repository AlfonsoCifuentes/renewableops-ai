# Contributing

RenewableOps AI uses short-lived feature branches and pull requests. Run
`make lint` and `make test` before opening a change. Never commit credentials,
raw tokens, personal data, or proprietary operational data.

Generated telemetry must retain `is_synthetic=true`. New external sources need
an entry in `data/source_registry.yaml`, license notes, a contract fixture, and
a checksum manifest.
