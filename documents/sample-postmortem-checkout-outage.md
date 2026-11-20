# Postmortem: Online Banking API 502 Outage (Sample)

Synthetic sample postmortem for demonstration.

## Summary

A configuration change to the online-banking-api readiness probe shipped with a deployment and marked healthy pods as unready. The load balancer drained the service over six minutes, producing 502 errors for digital banking traffic until the deployment was rolled back.

## Timeline

- 14:02 Deployment of online-banking-api v2.3.9 begins.
- 14:05 Error budget alert fires: 5xx rate above 5%.
- 14:07 On-call correlates the incident start with the deployment timestamp and inspects readiness-probe failures.
- 14:11 Rollback to v2.3.8 approved and started.
- 14:19 Error rate back to baseline; incident kept open for 15 minutes of stable metrics.

## Root cause

The readiness probe path was renamed in the application but not in the deployment manifest, so every new pod failed readiness while the application itself was healthy.

## Action items

1. Add a manifest-versus-application route check to the deployment pipeline.
2. Alert on readiness-probe failure rate separately from application errors.
3. Require a canary stage with automated 5xx comparison for API deployments.
