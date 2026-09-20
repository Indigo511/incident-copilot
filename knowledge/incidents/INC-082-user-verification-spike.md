# INC-082: User verification failures after client validation change

## Summary

User-induced card-unlock failures increased after a mobile client changed vehicle-number formatting. Backend availability and downstream health remained normal.

## Evidence

`INVALID_VEHICLE_NUMBER` increased only on mobile client 8.12. System-induced errors stayed below 1%, and the verification service remained healthy.

## Root cause

The client removed spaces before submission while an older backend validation rule expected the original formatted value. Valid users were rejected as invalid input.

## Resolution

The client change was disabled and the backend validator was updated to normalize supported vehicle-number formats.

## Prevention

Track failures by client version and validation rule. Add cross-platform contract tests for normalized vehicle identifiers.
