# Card Authorization Decline Spike Runbook

Synthetic sample document for demonstration.

## Symptoms

Card authorization decline rate rises sharply above baseline while approval traffic volume stays normal, or one card network reports elevated issuer timeouts.

## Response procedure

1. Compare the decline rate by network, issuer, and merchant category to isolate whether the spike is local or network-wide.
2. Check the card services deployment history and feature-flag changes in the last two hours.
3. Verify connectivity and latency to the card network endpoints; issuer timeouts present as soft declines.
4. Review fraud-rule and velocity-check changes; a new rule threshold is the most common internal cause of a sudden spike.
5. Check the HSM and tokenization service health if declines carry cryptographic error codes.
6. If a rule change caused the spike, roll back the rule configuration using the approved change process and monitor approval rate for 15 minutes.

## Escalation

Escalate to the payments team lead when the decline rate stays above twice the baseline for 20 minutes, and open a network bridge when the issue is confirmed on the card network side.
