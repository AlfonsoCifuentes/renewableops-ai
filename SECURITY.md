# Security policy

Report suspected vulnerabilities privately to the repository owner. Do not
open a public issue containing credentials, exploit payloads, or sensitive
logs.

The public application serves sanitized demonstration snapshots. It does not
control electrical assets and is not an operational SCADA system. Secrets are
read from environment variables; `.env` is ignored. Webhooks require HMAC in
non-demo environments and uploaded images are size- and type-limited.
