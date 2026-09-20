# INC-091: Verification service timeout degradation

## Summary

Card unlock requests timed out while the downstream verification service was degraded. No card-unlock deployment occurred during the incident window.

## Evidence

`VERIFICATION_SERVICE_TIMEOUT` dominated current logs. Distributed traces showed latency at the verification-service hop and dependency error rate exceeded 10%.

## Root cause

The verification service exhausted its database connection pool after a traffic increase. Card-unlock workers waited until their downstream timeout expired.

## Resolution

The verification-service pool was safely expanded, traffic was reduced, and queued work recovered. Card-unlock code was not rolled back.

## Prevention

Alert on downstream pool saturation and timeout budgets. Apply circuit breaking and graceful degradation where business rules allow it.
