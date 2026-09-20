# INC-104: Card unlock failures after v2.4

## Summary

At 10:07 UTC, unlock failures rose from 2% to 18% shortly after `card-unlock-service` v2.4 was deployed. The incident affected asset-card customers in ap-south-1.

## Evidence

91% of failed v2.4 requests returned `MALFORMED_VEHICLE_ID`. The same error remained below 1% on v2.3. User-induced `INVALID_VEHICLE_NUMBER` failures stayed close to the normal baseline.

## Root cause

The v2.4 request mapper sent `vehicle_id` to the verification service where the contract required `card_id`. The downstream service rejected the malformed identifier.

## Resolution

The incident commander rolled v2.4 back to v2.3. The system-induced failure rate returned to baseline within four minutes.

## Prevention

Add a contract test for the verification-service request schema and alert when error rates differ materially by deployment version.
