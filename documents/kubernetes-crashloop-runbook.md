# Kubernetes CrashLoopBackOff Runbook

Synthetic sample document for demonstration.

## Symptoms

Pods restart repeatedly with CrashLoopBackOff after a deployment or node change, and the service loses capacity as replicas cycle.

## Response procedure

1. Read the previous container logs (`kubectl logs --previous`) before the pod restarts again; the crash reason is almost always in the last log lines.
2. Check pod events for OOMKilled, image pull failures, and failing liveness probes; each has a different fix.
3. Compare the new container's environment variables and mounted config with the last healthy revision.
4. For OOMKilled, verify memory requests and limits against the service's measured working set before raising limits.
5. If the crash began with the new release and the error rate is rising, roll back the deployment to the previous revision.
6. Confirm the rollout completes and error rate returns to baseline before closing the incident.

## Escalation

Escalate to the platform team when nodes themselves are unhealthy (disk pressure, kubelet failures), not just the workload.
