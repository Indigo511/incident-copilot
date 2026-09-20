# Downstream verification degradation

## Detection

Look for verification timeouts, elevated downstream latency, circuit-breaker activity and dependency-specific error rates.

## Confirmation

Use distributed traces to confirm that latency or errors originate at the verification-service hop. Do not infer dependency failure from a generic HTTP 500 alone.

## Mitigation

Apply timeouts, circuit breaking, load shedding or graceful degradation according to business safety rules. Coordinate capacity changes with the dependency owner.

## Recovery

Confirm dependency error rate, card-unlock failure rate and queued work all return to normal. Continue monitoring for retry storms.
