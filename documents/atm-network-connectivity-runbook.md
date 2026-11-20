# ATM Network Connectivity Runbook

Synthetic sample document for demonstration.

## Symptoms

One ATM or a group of ATMs goes offline, shows out-of-service, or repeatedly connects and disconnects from the switch.

## Response procedure

1. Confirm scope from the ATM fleet dashboard: single unit, one site, or a regional group.
2. Check the site network circuit status and the last successful heartbeat timestamp.
3. For a single ATM, restart the ATM controller service remotely before dispatching a technician.
4. Verify the switch heartbeat and message queue for the affected terminal IDs.
5. If a whole site is down, check the site router and the carrier incident board; a carrier outage needs no ATM-side action.
6. After recovery, monitor the fleet dashboard for 15 minutes and confirm transaction success on each recovered unit.

## Escalation

Escalate to the network team when the circuit is down, and dispatch field service only after remote restart and circuit checks are complete.
