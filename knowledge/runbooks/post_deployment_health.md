# Post-deployment card-unlock health

## Scope

Use this runbook to assess card-unlock health after a deployment without assuming the deployment caused every nearby failure.

## Comparison window

Compare equivalent time windows, endpoints, regions, card types and client versions. Require adequate request counts before interpreting percentage differences.

## Healthy result

Report no material regression only when system and user failure rates remain within agreed thresholds and dependencies are healthy. Continue monitoring because a short window may miss delayed failures.

## Ambiguous changes

If multiple deployments, feature flags or configuration changes occurred, identify separate cohorts before attributing the incident. Abstain when attribution cannot be isolated.

## Approval boundary

The copilot may recommend rollback or traffic shifting, but a human incident commander must approve any mutation.
