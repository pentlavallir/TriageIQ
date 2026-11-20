# Database Connection Pool Exhaustion Runbook

Synthetic sample document for demonstration.

## Symptoms

Requests time out waiting for a database connection, the application logs connection pool exhaustion or "connection wait timeout" errors, and the database itself shows normal CPU with many idle or long-running sessions.

## Response procedure

1. Confirm the pool wait metric and the number of active connections per application instance.
2. Check for a recent traffic spike or a new deployment that raised the instance count without raising the pool budget.
3. Look for leaked connections: transactions opened without commit or rollback in the newest code path.
4. Identify long-running queries holding connections and capture their execution plans before killing any session.
5. If the pool is exhausted by a leak, restart the affected instances in small batches to return connections safely.
6. Raise the pool size only within the database connection budget agreed with the database team.

## Escalation

Escalate to the database team when connection-pool errors continue after application rollback, or when total connections approach the database limit across all services.
