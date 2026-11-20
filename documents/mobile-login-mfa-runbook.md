# Mobile Login and MFA Runbook

Synthetic sample document for demonstration.

## Symptoms

Members cannot log in to the mobile app, or MFA passcodes arrive late, fail validation, or loop back to the login screen after successful entry.

## Response procedure

1. Check the authentication service error rate and the MFA provider status page before changing any configuration.
2. Confirm whether failures affect all members or only one app version, one carrier, or one region.
3. Verify the authentication service clock offset; MFA time-based codes fail when server time drifts more than 30 seconds.
4. Check the session cache (Redis) health; a full or evicted session store forces repeated MFA challenges.
5. Review the latest mobile release and authentication deployment timestamps against the incident start time.
6. If the MFA provider is degraded, enable the approved fallback challenge method and post a member-facing status update.

## Escalation

Escalate to the identity team when MFA validation fails after provider recovery, and to the security team immediately if failure patterns suggest credential-stuffing traffic.
