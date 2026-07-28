CREATE CATALOG IF NOT EXISTS renewableops
COMMENT 'RenewableOps AI portfolio demonstration; no production SCADA data';

CREATE SCHEMA IF NOT EXISTS renewableops.dev
COMMENT 'Development objects for reproducible portfolio workflows';

CREATE VOLUME IF NOT EXISTS renewableops.dev.landing
COMMENT 'Bounded landing area for sanitized demo uploads';

CREATE VOLUME IF NOT EXISTS renewableops.dev.snapshots
COMMENT 'Sanitized public snapshot exports';
