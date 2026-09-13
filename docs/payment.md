# Payment and Invoice

## Configuration

Put sandbox values in the local `.env` file. The file is ignored by git.

```dotenv
SEPAY_ENV=sandbox
SEPAY_MERCHANT_ID=
SEPAY_SECRET_KEY=
SEPAY_CHECKOUT_URL=https://pay-sandbox.sepay.vn/v1/checkout/init
SEPAY_API_URL=https://pgapi-sandbox.sepay.vn
```

The secret is used only by `apps.payments.sepay.SePayService`; it is never
serialized to the API or dashboard.

## Database

```bash
python manage.py migrate
```

The migrations create `invoices_invoice`, `payments_payment`,
`payments_transaction`, and `payments_audit`. Provider transaction IDs are
unique per provider to make webhook retries idempotent.

## Product to payment flow

Orders use the existing `apps.product.models.Product` table and
`ProductSelector.get_sellable_product_for_update()`. The backend reads the
current `selling_price`, `name`, and `sku` while holding the Product row lock;
the client cannot supply a price. Each `OrderItem` stores those values as a
snapshot, so later Product edits do not change historical orders.

The normal flow is:

```text
Product -> Order -> OrderItem -> Invoice -> Payment -> PaymentTransaction
```

## API

All authenticated endpoints use the existing `/api/v1/` response envelope.

| Method | Path | Purpose |
| --- | --- | --- |
| GET, POST | `/api/v1/invoices/` | List or create invoices |
| GET | `/api/v1/invoices/<id>/` | Invoice, payment and transaction summary |
| POST | `/api/v1/invoices/<id>/` | Transition an invoice status |
| GET, POST | `/api/v1/orders/` | List or create orders from existing Products |
| GET | `/api/v1/orders/<id>/` | Order and item snapshots |
| POST | `/api/v1/orders/<id>/` | Transition an order status |
| GET, POST | `/api/v1/payments/` | List or create a QR payment |
| POST | `/api/v1/invoices/<id>/payments/` | Create QR or authorized manual payment from an Invoice |
| GET | `/api/v1/payments/<id>/` | Payment detail |
| POST | `/api/v1/payments/<id>/cancel/` | Cancel pending/processing payment |
| GET | `/api/v1/payments/<id>/status/` | Read status and expire stale pending payments |
| GET | `/api/v1/payments/<id>/transactions/` | Immutable transaction history |
| POST | `/api/v1/payments/<invoice-id>/manual/` | Authorized manual payment |
| POST | `/api/v1/payments/sepay/webhook/` | Verified SePay callback |

The dashboard exposes the same workflow under `/orders/` and `/invoices/` with
session auth. Product selectors on the order form are populated from the
existing Product queryset; no Product records are created by this flow.

## Flow

An invoice is created as `DRAFT`, moved to `PENDING_PAYMENT`, and can then
become `PAID` only after an authorized manual payment or a verified provider
callback. QR payments expire after 15 minutes and must be recreated. Payment
transactions are append-only history; manual edits create `PaymentAudit`
records instead of overwriting transaction rows.

## Sandbox checklist

1. Configure the four SePay sandbox environment variables.
2. Create an invoice and transition it to `PENDING_PAYMENT`.
3. Create a QR payment and verify the checkout fields contain no secret.
4. Send a signed sandbox callback and verify the transaction, payment, and invoice.
5. Send the same callback again and verify the transaction count is unchanged.
6. Verify invalid signature and amount mismatch are rejected.
7. Verify manual payment, expiry, and cancellation flows.
8. Run `python -m pytest -q` before deploying.