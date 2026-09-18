---
document_id: "LOST-01"
version: 1
title: "Lost or stolen phones"
category: "lost_device"
effective_from: "2026-01-01"
effective_to: null
locale: "en-US"
product: "mobile"
visibility: "public"
owner: "TT&T Fictional Policy Team"
reviewed_at: "2026-09-07"
synthetic: true
---

# Lost or stolen phones

## Support response
If a phone is lost, explain that suspension can stop mobile service on the affected line and may prevent use while the customer seeks help. Do not promise that it disables every device function, erases local data, or removes existing charges. Verify the affected line through the authorized account before discussing private account facts.

## MVP boundary
The two-day assistant cannot suspend or restore a line. It may create a requested urgent support ticket and explain the next steps. It must not say “your line is suspended” unless an authorized status lookup confirms an existing suspension. Historical fixture status is not evidence of a new action by the assistant.

## Future action
A future suspension capability requires explicit customer confirmation, policy and record-version checks, idempotent execution, and an audit record. SIM replacement, account recovery, and device tracking remain separate secure processes. Never ask for an authentication code to complete this chat handoff.
