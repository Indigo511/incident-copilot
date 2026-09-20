# Card unlock failures

## Purpose

Use this runbook when the `POST /v1/cards/unlock` failure rate exceeds 5% for five consecutive minutes.

## Initial triage

Compare error rates by deployment version, endpoint, region, card type, and failure category. Treat a new deployment as a hypothesis, not a confirmed cause.

## System-induced failures

Inspect `MALFORMED_VEHICLE_ID`, `VERIFICATION_SERVICE_TIMEOUT`, and `DB_CONNECTION_POOL_EXHAUSTED`. Check the request mapper, downstream verification-service health, and database connection-pool saturation.

## User-induced failures

Inspect `INVALID_VEHICLE_NUMBER` and `VERIFICATION_CODE_MISMATCH`. These should not cause an HTTP 5xx response. A rising user-induced rate may indicate a client UX issue or a changed validation rule.

## Safe remediation

Do not automatically roll back a deployment. First compare old and new versions using equivalent traffic. A human incident commander must approve rollback, traffic shifting, or feature-flag changes.
