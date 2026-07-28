-- Replace account groups to match the connected workspace before execution.
GRANT USE CATALOG ON CATALOG renewableops TO `account users`;
GRANT USE SCHEMA ON SCHEMA renewableops.dev TO `account users`;
GRANT SELECT ON FUTURE TABLES IN SCHEMA renewableops.dev TO `account users`;
GRANT READ VOLUME ON VOLUME renewableops.dev.snapshots TO `account users`;
