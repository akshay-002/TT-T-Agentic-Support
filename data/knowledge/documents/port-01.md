---
document_id: "PORT-01"
version: 1
title: "Keeping an existing number"
category: "number_porting"
effective_from: "2026-01-01"
effective_to: null
locale: "en-US"
product: "mobile"
visibility: "public"
owner: "TT&T Fictional Policy Team"
reviewed_at: "2026-09-07"
synthetic: true
---

# Keeping an existing number

## Transfer procedure
A number transfer is reviewed through the secure onboarding process. Customers should keep service with the prior carrier active until a transfer is confirmed complete. A transfer may need account details or a transfer PIN, but these must be supplied through the secure carrier workflow, never in chatbot messages.

## Status explanations
Requested means a transfer has been submitted in the simulation. In review means checks are incomplete. Completed means the operational transfer record confirms completion. A model-generated answer, order placement, or ticket creation cannot establish transfer completion. The dataset stores only masked number references and does not include PINs.

## MVP boundary
The two-day chatbot explains the policy and routes transfer problems to support. It does not submit, cancel, or retry a transfer. Do not promise a completion time absent from an authorized status record. A failed transfer should be escalated without asking the customer to paste sensitive credentials.
