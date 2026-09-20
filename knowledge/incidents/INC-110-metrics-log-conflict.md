# INC-110: Failure metric and log pipeline disagreement

## Summary

The card-unlock dashboard showed a sharp failure increase, but application logs and customer reports remained normal.

## Evidence

The failure counter increased while request totals, error logs and downstream health were stable. A second metrics source did not reproduce the spike.

## Root cause

A metrics-label change counted retries as new failures, inflating the dashboard without changing customer outcomes.

## Resolution

The metric query was corrected and historical dashboard panels were annotated. No application rollback occurred.

## Prevention

Cross-check high-impact alerts against logs, traces and a second metric. Version metric definitions alongside application changes.
