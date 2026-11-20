# Incident Severity and Escalation SOP

Synthetic sample document for demonstration.

## Severity definitions

- SEV1: a customer-facing service is down or a critical journey such as login, payments, or card authorization is unavailable. Page the incident commander and the service owner immediately.
- SEV2: a major function is degraded with a workaround available. Engage the service owner within 30 minutes.
- SEV3: minor impact or internal-only degradation. Handle in the normal support queue within one business day.

## First 15 minutes of any SEV1 or SEV2

1. Acknowledge the alert and open the incident record with start time, symptoms, and blast radius.
2. Check the change calendar for deployments or configuration changes in the last 60 minutes.
3. Post the first stakeholder update in the incident channel: impact, current hypothesis, next update time.
4. Assign one incident commander; responders do not self-assign parallel fixes.

## Escalation matrix

- Platform and infrastructure issues escalate to the platform on-call.
- Database issues escalate to the database on-call when errors persist after application rollback.
- Vendor or network issues escalate to the vendor bridge with the incident number in the subject line.
