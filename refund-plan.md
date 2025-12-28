# Refund Handling Logic - Rewrite Plan

## Overview

Two webhook handlers process Stripe refund lifecycle events:
1. **handle_refund_created** - Called when Stripe emits `charge.refund.created`
2. **handle_refund_confirmed** - Called when Stripe emits `charge.refund.updated` (refund finalized)

---

## Data Models Required

### Refund
| Field | Type | Description |
|-------|------|-------------|
| payment | FK→Payment | Parent payment being refunded |
| refund_code | string(40) | Stripe refund ID (`re_xxx`), **unique** |
| refund_amount | decimal(5,2) | Amount in currency units (dollars) |
| issuer | FK→User | Who initiated refund (system user or admin) |
| notes | text | Refund reason |
| confirmed | bool | True when Stripe finalizes refund |
| refund_date | datetime | Auto-set on creation |

### Payment
| Field | Type | Description |
|-------|------|-------------|
| payment_code | string(40) | Stripe PaymentIntent ID (`pi_xxx`) |
| user | FK→User | Who made the payment |
| event | FK→Event | Associated event |

---

## Stripe Webhook Payload (Input)

```json
{
  "id": "re_1abc123...",
  "payment_intent": "pi_1xyz789...",
  "reason": "requested_by_customer",
  "amount": 15000
}
```

Note: `amount` is in **cents** - must convert to dollars by dividing by 100.

---

## handle_refund_created Logic

### Input
- `refund` object from Stripe webhook

### Steps

1. **Extract fields from webhook payload**
   - `refund_id` = refund.id
   - `payment_intent_id` = refund.payment_intent
   - `reason` = refund.reason
   - `amount` = refund.amount / 100 (cents → dollars)

2. **Look up Payment by payment_code**
   - Query: `Payment WHERE payment_code = payment_intent_id`
   - If not found:
     - Log error: "Refund created but no payment found"
     - Return early with error result
     - **Do not create local Refund record**

3. **Get or create Refund record** (idempotent)
   - Query: `Refund WHERE refund_code = refund_id`
   - If exists: use existing record (webhook may have raced with API)
   - If not exists: create with:
     - `payment` = found Payment
     - `refund_code` = refund_id
     - `refund_amount` = amount
     - `issuer` = system user (see below)
     - `notes` = reason
     - `confirmed` = false

4. **Get or create system user for issuer**
   - Query: `User WHERE username = "stripe_system"`
   - If not exists: create with:
     - `username` = "stripe_system"
     - `email` = "stripe@system.local"
     - `is_active` = false
   - Use this user as `issuer` for webhook-initiated refunds

5. **Send refund notification email**
   - Recipient: payment.user.email
   - Include: event name, event date, refund amount, refund code
   - Catch and log any email errors (don't fail the task)

6. **Return result**
   ```json
   {
     "message": "Refund created",
     "payment_code": "<payment_intent_id>",
     "metadata": "Refund id: <refund_id>, amount: <amount>"
   }
   ```

### Error Handling
- Retry on transient failures (DB errors, network issues)
- Max 3 retries with exponential backoff
- Log all errors with refund_id and payment_intent_id for tracing

---

## handle_refund_confirmed Logic

### Input
- `refund` object from Stripe webhook (same structure as above)

### Steps

1. **Extract fields from webhook payload**
   - `refund_id` = refund.id
   - `payment_intent_id` = refund.payment_intent
   - `amount` = refund.amount / 100

2. **Look up Refund by refund_code**
   - Query: `Refund WHERE refund_code = refund_id`
   - If not found:
     - Log warning: "Refund not found, will retry"
     - **Throw error to trigger retry** (see race condition note)

3. **Update Refund record**
   - Set `confirmed` = true
   - Save

4. **Return result**
   ```json
   {
     "message": "Refund confirmed",
     "payment_code": "<payment_intent_id>",
     "metadata": "Refund id: <refund_id>, amount: <amount>"
   }
   ```

### Error Handling
- **Critical**: Must retry if refund not found
  - The "updated" webhook can arrive before "created" task completes
  - Retry allows time for creation to finish
- Max 3 retries with exponential backoff

---

## Race Condition Handling

### Scenario 1: Webhook vs Webhook
- "refund.updated" webhook may arrive before "refund.created" task finishes
- Solution: `handle_refund_confirmed` retries until Refund record exists

### Scenario 2: API vs Webhook
- Admin creates refund via API → triggers Stripe refund → webhook fires
- Both API and webhook try to create same Refund record
- Solution: Use `get_or_create` or handle unique constraint violation
  - If record exists, return existing (don't fail)

---

## Key Implementation Notes

1. **Idempotency**: Both handlers must be safe to call multiple times with same input
2. **Currency conversion**: Stripe uses cents; local DB uses dollars
3. **System user**: Webhook-initiated refunds use a special non-human user
4. **Email failures non-fatal**: Notification failure shouldn't fail the refund task
5. **Unique constraint**: `refund_code` must be unique to prevent duplicates
6. **Async processing**: These should run in background workers, not block webhook response

---

## Unresolved Questions

1. Should email notification also be sent on confirmation (currently only on creation)?
2. What should happen if Payment exists but is not confirmed?
3. Should there be a maximum age for Refund records to accept confirmation updates?
