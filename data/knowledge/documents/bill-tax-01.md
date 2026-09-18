---
document_id: "BILL-TAX-01"
version: 1
title: "Invoices and simulated taxes"
category: "billing_tax"
effective_from: "2026-01-01"
effective_to: null
locale: "en-US"
product: "mobile"
visibility: "public"
owner: "TT&T Fictional Policy Team"
reviewed_at: "2026-09-07"
synthetic: true
---

# Invoices and simulated taxes

## Invoice calculation
An invoice total is the sum of its signed line items in integer cents. Promotion credits are negative amounts. Zero-value informational items are permitted. The outstanding balance equals the total minus settled successful payments; failed or pending attempts do not reduce it.

## Tax fixture
For this synthetic dataset, account ACC identifiers must never be embedded into knowledge chunks. Most fixture invoices contain a fixed $5.00 simulated tax adjustment. A fixture exemption can instead produce $0.00. These are testing amounts, not actual tax rules or a jurisdictional rate. Use the invoice item as authority for a particular customer and never calculate real taxes from this document.

## Billing period
Fixture invoices cover a calendar month, issue on the first day of the following month, and are due on the fifteenth. Compare matching account invoices and explain the itemized changes. A service outage does not automatically alter an invoice or create a credit.
