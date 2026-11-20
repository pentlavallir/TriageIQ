# API Gateway 5xx Runbook

Synthetic sample document for demonstration.

## Symptoms

The API gateway returns elevated 500, 502, or 504 responses while backend services report healthy, or one route shows errors while others stay clean.

## Response procedure

1. Break down the 5xx rate by route, upstream service, and gateway node to find the failing path.
2. Check upstream health endpoints directly, bypassing the gateway, to separate gateway faults from service faults.
3. Review gateway configuration changes: route weights, timeout values, and TLS certificate rotations.
4. Inspect gateway node CPU, memory, and connection counts; a saturated node drops upstream connections under load.
5. For 504 errors, compare gateway timeout settings with the upstream service's p99 latency before raising any timeout.
6. If a configuration change correlates with the errors, roll back the gateway configuration bundle and watch the 5xx rate for 10 minutes.

## Escalation

Escalate to the platform team when all gateway nodes are saturated, and to the service owner when a single upstream fails its direct health checks.
