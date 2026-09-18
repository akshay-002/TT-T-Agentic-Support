---
document_id: "ACCOUNT-01"
version: 1
title: "Account access and changes"
category: "account"
effective_from: "2026-01-01"
effective_to: null
locale: "en-US"
product: "mobile"
visibility: "public"
owner: "TT&T Fictional Policy Team"
reviewed_at: "2026-09-07"
synthetic: true
---

# Account access and changes

## Account scope
An authenticated session maps to an authorized account. Names, email addresses, invoice IDs, and masked phone numbers supplied in chat do not establish ownership. Each backend lookup checks that the referenced record belongs to the session account. Being in the same service area does not grant access to another customer's records.

## Changes
The two-day demonstration uses seeded accounts and supports no real identity recovery, ownership transfer, or address update. Explain the relevant process and offer a support ticket. Any later profile change requires the approved secure flow and server-side authorization.

## Privacy
Only necessary account details should appear in a response. Do not disclose full customer lists or internal credentials. Fixture principals are test identifiers, not bearer tokens and not a production authentication system. A public demo must bind them to server-issued sessions and must not accept an arbitrary principal ID from a customer message.
