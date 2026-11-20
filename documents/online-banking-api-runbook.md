# Online Banking API Production Runbook

## Service overview

The Online Banking API receives digital banking requests from the web and mobile applications and communicates with the Payment Gateway, Card Services, Redis session cache, and the PostgreSQL accounts database. Production traffic enters through the public load balancer and is forwarded to the online-banking-api Kubernetes deployment.

## 502 errors after a deployment

When 502 responses begin immediately after a release, the on-call engineer should use the following order of checks:

1. Compare the incident start time with the latest deployment timestamp.
2. Check Kubernetes deployment and pod status for `online-banking-api`.
3. Inspect readiness-probe failures before restarting pods. A pod that fails readiness must not receive production traffic.
4. Review the latest online-banking-api application logs for startup, dependency, or configuration errors.
5. Verify that required environment variables and secrets are present in the new deployment.
6. Check connectivity from online-banking-api to the Payment Gateway and the accounts database.
7. If the new release is strongly correlated with the incident and the error rate remains above 5% for five minutes, roll back to the last known healthy image using the approved deployment rollback procedure.

Do not delete pods repeatedly as a first response. Preserve logs and events needed for diagnosis.

## Escalation

Escalate to the platform team when the load balancer cannot reach healthy online-banking-api pods even though readiness checks are passing. Escalate to the database team when connection-pool errors continue after application rollback.
