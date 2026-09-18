# Data dictionary

All records are fictional. Currency values are signed integer US cents unless constrained otherwise. Null is unknown or not applicable except `plans.data_allowance_mb`, where it means unlimited. Boolean flags are 0 or 1 for SQL portability. UTC timestamps are ISO 8601 text. Dates are ISO calendar dates. `user_id` is the person fixture; `account_id` owns customer records; `principal_id` binds a test session. Never treat any ID as an authentication secret.

## users

| Field | Type and constraints |
|---|---|
| `user_id` | `TEXT PRIMARY KEY` |
| `principal_id` | `TEXT NOT NULL UNIQUE` |
| `display_name` | `TEXT NOT NULL` |
| `email` | `TEXT NOT NULL UNIQUE` |
| `created_at` | `TEXT NOT NULL` |

## accounts

| Field | Type and constraints |
|---|---|
| `account_id` | `TEXT PRIMARY KEY` |
| `user_id` | `TEXT NOT NULL UNIQUE REFERENCES users(user_id)` |
| `status` | `TEXT NOT NULL CHECK(status IN ('active','restricted'))` |
| `address` | `TEXT NOT NULL` |
| `postal_code` | `TEXT NOT NULL` |
| `service_area` | `TEXT NOT NULL` |
| `created_at` | `TEXT NOT NULL` |

## plans

| Field | Type and constraints |
|---|---|
| `plan_id` | `TEXT PRIMARY KEY` |
| `name` | `TEXT NOT NULL` |
| `monthly_price_cents` | `INTEGER NOT NULL CHECK(monthly_price_cents >= 0)` |
| `data_allowance_mb` | `INTEGER` |
| `hotspot_allowance_mb` | `INTEGER NOT NULL` |
| `supports_5g` | `INTEGER NOT NULL CHECK(supports_5g IN (0,1))` |
| `plan_type` | `TEXT NOT NULL` |
| `effective_from` | `TEXT NOT NULL` |
| `effective_to` | `TEXT` |

## lines

| Field | Type and constraints |
|---|---|
| `line_id` | `TEXT PRIMARY KEY` |
| `account_id` | `TEXT NOT NULL REFERENCES accounts(account_id)` |
| `masked_phone` | `TEXT NOT NULL UNIQUE` |
| `status` | `TEXT NOT NULL CHECK(status IN ('active','suspended'))` |
| `version` | `INTEGER NOT NULL CHECK(version > 0)` |
| `activated_at` | `TEXT NOT NULL` |

## subscriptions

| Field | Type and constraints |
|---|---|
| `subscription_id` | `TEXT PRIMARY KEY` |
| `line_id` | `TEXT NOT NULL UNIQUE REFERENCES lines(line_id)` |
| `plan_id` | `TEXT NOT NULL REFERENCES plans(plan_id)` |
| `start_date` | `TEXT NOT NULL` |
| `end_date` | `TEXT` |

## devices

| Field | Type and constraints |
|---|---|
| `device_id` | `TEXT PRIMARY KEY` |
| `line_id` | `TEXT NOT NULL UNIQUE REFERENCES lines(line_id)` |
| `brand` | `TEXT NOT NULL` |
| `model` | `TEXT NOT NULL` |
| `esim_supported` | `INTEGER NOT NULL CHECK(esim_supported IN (0,1))` |
| `upgrade_eligible` | `INTEGER NOT NULL CHECK(upgrade_eligible IN (0,1))` |
| `monthly_installment_cents` | `INTEGER NOT NULL CHECK(monthly_installment_cents >= 0)` |

## invoices

| Field | Type and constraints |
|---|---|
| `invoice_id` | `TEXT PRIMARY KEY` |
| `account_id` | `TEXT NOT NULL REFERENCES accounts(account_id)` |
| `period_start` | `TEXT NOT NULL` |
| `period_end` | `TEXT NOT NULL` |
| `issued_at` | `TEXT NOT NULL` |
| `due_date` | `TEXT NOT NULL` |
| `currency` | `TEXT NOT NULL CHECK(currency = 'USD')` |
| `total_cents` | `INTEGER NOT NULL CHECK(total_cents >= 0)` |
| `amount_paid_cents` | `INTEGER NOT NULL CHECK(amount_paid_cents >= 0)` |
| `balance_due_cents` | `INTEGER NOT NULL CHECK(balance_due_cents >= 0)` |
| `status` | `TEXT NOT NULL CHECK(status IN ('paid','open'))` |

## invoice_items

| Field | Type and constraints |
|---|---|
| `item_id` | `TEXT PRIMARY KEY` |
| `invoice_id` | `TEXT NOT NULL REFERENCES invoices(invoice_id)` |
| `line_id` | `TEXT REFERENCES lines(line_id)` |
| `item_type` | `TEXT NOT NULL CHECK(item_type IN ('plan_charge','device_installment','promotion_credit','tax','activation_fee','roaming_pass'))` |
| `description` | `TEXT NOT NULL` |
| `amount_cents` | `INTEGER NOT NULL` |
| `policy_id` | `TEXT NOT NULL` |
| `service_event_id` | `TEXT` |

## payments

| Field | Type and constraints |
|---|---|
| `payment_id` | `TEXT PRIMARY KEY` |
| `invoice_id` | `TEXT NOT NULL UNIQUE REFERENCES invoices(invoice_id)` |
| `attempted_amount_cents` | `INTEGER NOT NULL CHECK(attempted_amount_cents >= 0)` |
| `settled_amount_cents` | `INTEGER NOT NULL CHECK(settled_amount_cents >= 0)` |
| `status` | `TEXT NOT NULL CHECK(status IN ('succeeded','pending','failed'))` |
| `method_type` | `TEXT NOT NULL` |
| `failure_code` | `TEXT` |
| `created_at` | `TEXT NOT NULL` |

## usage_records

| Field | Type and constraints |
|---|---|
| `usage_id` | `TEXT PRIMARY KEY` |
| `line_id` | `TEXT NOT NULL REFERENCES lines(line_id)` |
| `period_start` | `TEXT NOT NULL` |
| `period_end` | `TEXT NOT NULL` |
| `data_mb` | `INTEGER NOT NULL CHECK(data_mb >= 0)` |
| `hotspot_mb` | `INTEGER NOT NULL CHECK(hotspot_mb >= 0)` |
| `voice_minutes` | `INTEGER NOT NULL CHECK(voice_minutes >= 0)` |
| `sms_count` | `INTEGER NOT NULL CHECK(sms_count >= 0)` |

## outages

| Field | Type and constraints |
|---|---|
| `outage_id` | `TEXT PRIMARY KEY` |
| `service_area` | `TEXT NOT NULL` |
| `postal_code` | `TEXT NOT NULL` |
| `network_type` | `TEXT NOT NULL` |
| `status` | `TEXT NOT NULL CHECK(status IN ('active','resolved','investigating'))` |
| `started_at` | `TEXT NOT NULL` |
| `observed_at` | `TEXT NOT NULL` |
| `estimated_resolution` | `TEXT` |
| `resolved_at` | `TEXT` |
| `summary` | `TEXT NOT NULL` |

## support_tickets

| Field | Type and constraints |
|---|---|
| `ticket_id` | `TEXT PRIMARY KEY` |
| `account_id` | `TEXT NOT NULL REFERENCES accounts(account_id)` |
| `line_id` | `TEXT REFERENCES lines(line_id)` |
| `category` | `TEXT NOT NULL` |
| `summary` | `TEXT NOT NULL` |
| `status` | `TEXT NOT NULL CHECK(status IN ('open','in_review','resolved'))` |
| `created_at` | `TEXT NOT NULL` |
| `updated_at` | `TEXT NOT NULL` |
| `resolved_at` | `TEXT` |
| `idempotency_key` | `TEXT NOT NULL UNIQUE` |

## connection_requests

| Field | Type and constraints |
|---|---|
| `request_id` | `TEXT PRIMARY KEY` |
| `account_id` | `TEXT NOT NULL REFERENCES accounts(account_id)` |
| `requested_lines` | `INTEGER NOT NULL CHECK(requested_lines > 0)` |
| `postal_code` | `TEXT NOT NULL` |
| `selected_plan_id` | `TEXT NOT NULL REFERENCES plans(plan_id)` |
| `status` | `TEXT NOT NULL` |
| `created_at` | `TEXT NOT NULL` |

## orders

| Field | Type and constraints |
|---|---|
| `order_id` | `TEXT PRIMARY KEY` |
| `request_id` | `TEXT NOT NULL UNIQUE REFERENCES connection_requests(request_id)` |
| `account_id` | `TEXT NOT NULL REFERENCES accounts(account_id)` |
| `line_id` | `TEXT NOT NULL REFERENCES lines(line_id)` |
| `status` | `TEXT NOT NULL` |
| `sim_type` | `TEXT NOT NULL` |
| `created_at` | `TEXT NOT NULL` |
| `completed_at` | `TEXT` |

## activations

| Field | Type and constraints |
|---|---|
| `activation_id` | `TEXT PRIMARY KEY` |
| `order_id` | `TEXT NOT NULL UNIQUE REFERENCES orders(order_id)` |
| `line_id` | `TEXT NOT NULL UNIQUE REFERENCES lines(line_id)` |
| `status` | `TEXT NOT NULL` |
| `activated_at` | `TEXT` |
| `fee_posted_invoice_id` | `TEXT REFERENCES invoices(invoice_id)` |

## number_port_requests

| Field | Type and constraints |
|---|---|
| `port_request_id` | `TEXT PRIMARY KEY` |
| `request_id` | `TEXT NOT NULL UNIQUE REFERENCES connection_requests(request_id)` |
| `line_id` | `TEXT NOT NULL REFERENCES lines(line_id)` |
| `old_carrier` | `TEXT NOT NULL` |
| `requested_number_masked` | `TEXT NOT NULL` |
| `status` | `TEXT NOT NULL` |
| `requested_at` | `TEXT NOT NULL` |
| `completed_at` | `TEXT` |
| `status_detail` | `TEXT NOT NULL` |

## account_history

| Field | Type and constraints |
|---|---|
| `event_id` | `TEXT PRIMARY KEY` |
| `account_id` | `TEXT NOT NULL REFERENCES accounts(account_id)` |
| `line_id` | `TEXT REFERENCES lines(line_id)` |
| `event_type` | `TEXT NOT NULL` |
| `occurred_at` | `TEXT NOT NULL` |
| `summary` | `TEXT NOT NULL` |
| `related_record_id` | `TEXT` |

## runs

| Field | Type and constraints |
|---|---|
| `run_id` | `TEXT PRIMARY KEY` |
| `account_id` | `TEXT NOT NULL REFERENCES accounts(account_id)` |
| `principal_id` | `TEXT NOT NULL REFERENCES users(principal_id)` |
| `intent` | `TEXT NOT NULL` |
| `status` | `TEXT NOT NULL` |
| `started_at` | `TEXT NOT NULL` |
| `completed_at` | `TEXT NOT NULL` |
| `policy_version` | `TEXT NOT NULL` |
| `tool_call_count` | `INTEGER NOT NULL CHECK(tool_call_count >= 0)` |

## audit_events

| Field | Type and constraints |
|---|---|
| `audit_id` | `TEXT PRIMARY KEY` |
| `run_id` | `TEXT NOT NULL REFERENCES runs(run_id)` |
| `account_id` | `TEXT NOT NULL REFERENCES accounts(account_id)` |
| `event_type` | `TEXT NOT NULL` |
| `reason_code` | `TEXT NOT NULL` |
| `occurred_at` | `TEXT NOT NULL` |

## Cross-table application invariants

SQL foreign keys establish existence, not ownership across every join. Validate that invoice items, tickets, orders and activations reference lines of the same account. Validate payment/invoice reconciliation and plan price matches. The verifier exercises these invariants. Production applications still need authentication, row-level security or equivalent scoped services, safe migrations and typed timestamp columns.
