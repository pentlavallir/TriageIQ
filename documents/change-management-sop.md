# Change Management and Rollback SOP

Synthetic sample document for demonstration.

## Standard change requirements

- Every production change records the service, version, owner, start window, and rollback plan before deployment.
- Deployments outside the approved window require duty-manager approval.
- Database migrations must be backward-compatible with the previous application version.

## During a change

1. Announce the start in the incident channel with the change record number.
2. Watch the service error rate, latency, and one business health check for the first 15 minutes.
3. Stop the rollout and roll back if the error rate exceeds 5% for five minutes or the business health check fails.

## After a change

- Confirm the change record shows the final deployed version and the verification result.
- Link any incident opened during the window to the change record for postmortem review.
