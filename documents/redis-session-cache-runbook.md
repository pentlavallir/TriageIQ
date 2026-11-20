# Redis Session Cache Runbook

Synthetic sample document for demonstration.

## Symptoms

Users are logged out unexpectedly, session lookups time out, or cache memory usage climbs until evictions spike.

## Response procedure

1. Check cluster health, replication lag, and the evicted-keys metric before touching configuration.
2. Identify whether memory growth comes from a new key pattern or a missing TTL in a recent release.
3. Verify the failover state; a half-completed failover leaves applications writing to a read-only replica.
4. If evictions are caused by one keyspace, apply the approved per-keyspace memory policy rather than raising total memory.
5. Restart application session managers only if connections are stuck on a dead primary after failover completes.
6. Monitor session error rate and eviction rate for 15 minutes after the fix.

## Escalation

Escalate to the platform team for cluster-level failures, and to the application team when a release introduced keys without TTLs.
