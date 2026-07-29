# Security scan disposition

## EX-2026-001 — Next.js embedded build dependencies

- Reviewed: 2026-07-29
- Owner: Platform
- Status: temporary accepted risk
- Scope: `next@16.2.12` embeds `postcss@8.4.31` and optional
  `sharp@0.34.5`; `npm audit --omit=dev` reports three high-severity findings
  and zero critical findings, with no non-breaking Next.js remediation.
- Exposure: the application does not accept user CSS, source maps or image
  transformation requests; charts contain bounded internal data and no
  `next/image` endpoint is used. Runtime is bound to loopback by default.
- Compensating controls: CSP/security headers, static trusted CSS, upload
  decoding in FastAPI, locked dependencies, production container non-root.
- Decision: do not downgrade to an obsolete Next.js release suggested by npm.
- Exit: upgrade when the stable Next.js line ships fixed embedded versions;
  re-run `npm audit --omit=dev` in every weekly review.

ECharts and Vitest advisories were remediated by upgrading to 6.1.0 and 4.1.10.
This exception is not permission to expose the local demo as an internet
service.

## EX-2026-002 — ESLint development dependency chain

- Reviewed: 2026-07-29
- Owner: Frontend
- Status: temporary accepted risk
- Scope: npm reports high-severity advisories in the ESLint-only
  `@eslint/eslintrc` / `minimatch` dependency chain. The affected packages are
  development tooling and are not copied into the production standalone image.
- Exposure: lint runs only against trusted repository source in CI and on the
  developer workstation. User input is never passed to ESLint or its globbing
  expressions.
- Compensating controls: read-only CI token, locked dependency graph,
  production multi-stage build, critical audit gate and weekly dependency
  review.
- Exit: remove the exception as soon as the stable ESLint dependency graph
  consumes a patched minimatch release; keep `npm audit --omit=dev` as the
  runtime gate.
