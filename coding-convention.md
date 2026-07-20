# Python & Django Coding Convention

**Project:** POS Management System\
**Version:** 1.0.0\
**Status:** Mandatory\
**Applies to:** Python, Django, Django REST Framework (DRF),
integrations, tests, scripts, and AI-generated code.

------------------------------------------------------------------------

## 1. Purpose

This document defines the mandatory coding standards for the POS
Management project.

The goals are:

-   Maintain consistent and readable code.
-   Reduce bugs and technical debt.
-   Make code easy to review and maintain.
-   Ensure all developers and AI coding assistants follow the same
    rules.
-   Follow established Python and Django best practices.

------------------------------------------------------------------------

# 2. Standards Hierarchy

When there is a conflict, follow this priority:

1.  **Python language conventions and PEP 8**
2.  **PEP 257 for docstrings**
3.  **PEP 484 / type hints**
4.  **Django official conventions**
5.  **Django REST Framework conventions**
6.  **This project coding convention**
7.  **Personal coding preference**

Do not introduce a personal style that conflicts with this document.

------------------------------------------------------------------------

# 3. General Engineering Principles

All code MUST follow:

-   KISS --- Keep It Simple, Stupid.
-   DRY --- Don't Repeat Yourself.
-   SOLID where applicable.
-   Separation of Concerns.
-   Explicit is better than implicit.
-   Fail fast and fail clearly.
-   Prefer readable code over clever code.
-   Avoid premature optimization.
-   Do not over-engineer simple business requirements.

## 3.1 Business Logic Rule

Business logic MUST NOT be scattered across:

-   Views
-   Serializers
-   URL files
-   Templates
-   Signals

Complex business logic MUST be placed in a dedicated service layer.

Example:

``` python
# Bad
class PaymentView(APIView):
    def post(self, request):
        invoice = Invoice.objects.get(id=request.data["invoice_id"])
        invoice.status = "PAID"
        invoice.save()
        # More business logic here...


# Good
class PaymentService:
    @staticmethod
    def confirm_payment(invoice, payment_data):
        # Business logic belongs here.
        pass
```

------------------------------------------------------------------------

# 4. Python Version

The project MUST define and use one Python version consistently.

Recommended:

``` text
Python 3.12+
```

The exact version MUST be pinned in project documentation and deployment
configuration.

Example:

``` text
.python-version
```

or:

``` text
requires-python = ">=3.12,<3.13"
```

------------------------------------------------------------------------

# 5. Formatting

## 5.1 Formatter

The project MUST use:

``` text
Black
```

Recommended line length:

``` text
88 characters
```

Example:

``` bash
black .
```

Do not manually format code differently from the configured formatter.

## 5.2 Import Sorting

Use:

``` text
isort
```

Example:

``` bash
isort .
```

Import order:

1.  Standard library
2.  Third-party libraries
3.  Django
4.  Local application imports

Example:

``` python
import logging
from datetime import datetime

from django.db import transaction
from rest_framework import status

from apps.invoices.models import Invoice
from apps.payments.services import PaymentService
```

------------------------------------------------------------------------

# 6. Linting and Static Analysis

The project SHOULD use:

``` text
Ruff
```

Ruff is preferred for linting and many code-quality checks.

Recommended tools:

``` text
ruff
black
isort
mypy
pytest
```

A developer MUST NOT commit code with unresolved critical lint errors.

------------------------------------------------------------------------

# 7. Naming Conventions

## 7.1 Variables

Use `snake_case`.

``` python
invoice_total = 100000
payment_status = "SUCCESS"
```

Do not use:

``` python
invoiceTotal = 100000
```

## 7.2 Functions

Use `snake_case` and a verb-oriented name.

``` python
def calculate_invoice_total():
    pass


def create_payment():
    pass


def validate_webhook_signature():
    pass
```

Avoid vague names:

``` python
def process():
    pass
```

Prefer:

``` python
def process_payment_webhook():
    pass
```

## 7.3 Classes

Use `PascalCase`.

``` python
class PaymentService:
    pass


class InvoiceSerializer:
    pass
```

## 7.4 Constants

Use `UPPER_SNAKE_CASE`.

``` python
MAX_RETRY_COUNT = 3
DEFAULT_PAGE_SIZE = 20
PAYMENT_TIMEOUT_SECONDS = 300
```

## 7.5 Boolean Variables

Use prefixes such as:

``` python
is_active
has_payment
can_refund
should_retry
```

Avoid:

``` python
active
payment
```

when the value is boolean and the meaning is ambiguous.

------------------------------------------------------------------------

# 8. Type Hints

New code SHOULD use type hints.

Example:

``` python
def calculate_total(
    subtotal: int,
    vat_amount: int,
) -> int:
    return subtotal + vat_amount
```

For collections:

``` python
from typing import Iterable

def get_product_ids(products: Iterable[int]) -> list[int]:
    return list(products)
```

Use modern Python syntax where supported:

``` python
def get_user(user_id: int) -> User | None:
    ...
```

Avoid unnecessary `Any`.

Bad:

``` python
def process(data: Any) -> Any:
    pass
```

Use a specific type whenever possible.

------------------------------------------------------------------------

# 9. Functions

A function SHOULD:

-   Have one clear responsibility.
-   Be short enough to understand easily.
-   Avoid hidden side effects.
-   Have a meaningful name.

Bad:

``` python
def process_order():
    # Validate customer
    # Calculate price
    # Create invoice
    # Process payment
    # Update inventory
    # Send email
    # Create audit log
    pass
```

Good:

``` python
def create_order():
    validate_order()
    calculate_order_total()
    create_invoice()
```

Complex workflows SHOULD be orchestrated by a service.

------------------------------------------------------------------------

# 10. Exception Handling

## 10.1 Never Silently Ignore Exceptions

Bad:

``` python
try:
    process_payment()
except Exception:
    pass
```

Good:

``` python
try:
    process_payment()
except PaymentGatewayError as exc:
    logger.exception("Payment processing failed: %s", exc)
    raise
```

## 10.2 Catch Specific Exceptions

Bad:

``` python
except Exception:
    pass
```

Good:

``` python
except Invoice.DoesNotExist:
    ...
```

## 10.3 Do Not Use Exceptions for Normal Business Flow

Bad:

``` python
try:
    product = Product.objects.get(id=product_id)
except Product.DoesNotExist:
    product = None
```

Prefer:

``` python
product = Product.objects.filter(id=product_id).first()
```

when absence is an expected condition.

------------------------------------------------------------------------

# 11. Logging

Use Python logging.

``` python
import logging

logger = logging.getLogger(__name__)
```

Example:

``` python
logger.info(
    "Payment confirmed",
    extra={
        "invoice_id": invoice.id,
        "transaction_id": transaction_id,
    },
)
```

Do not use:

``` python
print("Payment successful")
```

in production code.

## Never Log Sensitive Data

Do not log:

-   Passwords
-   JWT tokens
-   API keys
-   Secret keys
-   Full payment credentials
-   Sensitive personal data

------------------------------------------------------------------------

# 12. Django Project Structure

Recommended structure:

``` text
project/
├── manage.py
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   ├── production.py
│   │   └── test.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── apps/
│   ├── authentication/
│   ├── users/
│   ├── customers/
│   ├── products/
│   ├── inventory/
│   ├── invoices/
│   ├── payments/
│   ├── reports/
│   ├── ai_insight/
│   └── audit_logs/
│
├── tests/
├── requirements/
├── scripts/
├── docs/
└── README.md
```

Each Django app SHOULD follow:

``` text
app_name/
├── __init__.py
├── admin.py
├── apps.py
├── models.py
├── serializers.py
├── urls.py
├── views.py
├── services.py
├── selectors.py
├── permissions.py
├── constants.py
├── exceptions.py
├── migrations/
└── tests/
```

Only create files when they are needed.

------------------------------------------------------------------------

# 13. Django Models

## 13.1 Model Naming

Use singular PascalCase.

``` python
class Product(models.Model):
    pass


class Invoice(models.Model):
    pass
```

## 13.2 Database Fields

Use clear names.

``` python
created_at
updated_at
deleted_at
total_amount
payment_status
```

Avoid:

``` python
date
value
status1
data
```

when the meaning is unclear.

## 13.3 Timestamps

Most business entities SHOULD have:

``` python
created_at
updated_at
```

Example:

``` python
created_at = models.DateTimeField(auto_now_add=True)
updated_at = models.DateTimeField(auto_now=True)
```

## 13.4 Monetary Values

Never use `FloatField` for money.

Bad:

``` python
price = models.FloatField()
```

Good:

``` python
price = models.DecimalField(
    max_digits=15,
    decimal_places=2,
)
```

## 13.5 Status Fields

Use Django `TextChoices`.

``` python
class PaymentStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PROCESSING = "PROCESSING", "Processing"
    SUCCESS = "SUCCESS", "Success"
    FAILED = "FAILED", "Failed"
```

Do not scatter raw strings throughout the code.

Bad:

``` python
payment.status = "SUCCESS"
```

Prefer:

``` python
payment.status = PaymentStatus.SUCCESS
```

------------------------------------------------------------------------

# 14. Database Transactions

Use `transaction.atomic()` for operations that must succeed or fail
together.

Example:

``` python
from django.db import transaction


@transaction.atomic
def confirm_payment(payment_id: int) -> None:
    payment = Payment.objects.select_for_update().get(
        id=payment_id,
    )

    payment.mark_success()
    payment.invoice.mark_paid()
    payment.invoice.update_inventory()
```

For payment processing, invoice updates and inventory updates MUST be
designed carefully to avoid partial state.

------------------------------------------------------------------------

# 15. Database Query Rules

## Avoid N+1 Queries

Bad:

``` python
for invoice in invoices:
    print(invoice.customer.name)
```

Use:

``` python
invoices = Invoice.objects.select_related("customer")
```

For many-to-many or reverse relations:

``` python
products = Product.objects.prefetch_related("categories")
```

## Do Not Query in Loops Without Reason

Bad:

``` python
for product_id in product_ids:
    Product.objects.get(id=product_id)
```

Prefer:

``` python
products = Product.objects.filter(id__in=product_ids)
```

## Use `select_for_update()` for Concurrent Business Operations

Especially for:

-   Payment confirmation
-   Inventory deduction
-   Stock adjustment

Example:

``` python
product = Product.objects.select_for_update().get(
    id=product_id,
)
```

------------------------------------------------------------------------

# 16. Service Layer

Services contain business operations that involve multiple models or
complex workflows.

Example:

``` python
class PaymentService:

    @staticmethod
    @transaction.atomic
    def confirm_payment(
        *,
        invoice: Invoice,
        transaction_id: str,
        amount: Decimal,
    ) -> Payment:
        ...
```

Services SHOULD:

-   Be deterministic where possible.
-   Receive explicit inputs.
-   Return meaningful results.
-   Raise domain-specific exceptions.
-   Avoid direct HTTP response handling.

Bad:

``` python
class PaymentService:
    def confirm_payment(self, request):
        return Response(...)
```

Good:

``` python
class PaymentService:
    def confirm_payment(self, invoice, payment_data):
        return payment
```

The view handles the HTTP response.

------------------------------------------------------------------------

# 17. Selector Layer

Selectors are used for read/query logic.

Example:

``` python
class InvoiceSelector:

    @staticmethod
    def get_by_id(invoice_id: int) -> Invoice | None:
        return (
            Invoice.objects
            .select_related("customer")
            .filter(id=invoice_id)
            .first()
        )
```

Use selectors when:

-   Queries are reused.
-   Query logic is complex.
-   Query optimization needs to be centralized.

------------------------------------------------------------------------

# 18. Django REST Framework

## 18.1 Views

Views SHOULD be thin.

Bad:

``` python
class PaymentView(APIView):
    def post(self, request):
        # 100 lines of business logic
        pass
```

Good:

``` python
class PaymentView(APIView):

    def post(self, request):
        serializer = PaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payment = PaymentService.create_payment(
            **serializer.validated_data,
        )

        return Response(
            PaymentResponseSerializer(payment).data,
        )
```

## 18.2 Serializers

Serializers handle:

-   Input validation.
-   Output serialization.
-   Simple transformation.

Complex business logic SHOULD NOT be implemented in serializers.

## 18.3 API Response Format

Use a consistent response format.

Success:

``` json
{
  "success": true,
  "data": {},
  "message": "Request successful"
}
```

Error:

``` json
{
  "success": false,
  "error": {
    "code": "INVOICE_NOT_FOUND",
    "message": "Invoice was not found"
  }
}
```

## 18.4 HTTP Status Codes

Use correct HTTP status codes:

``` text
200 OK
201 CREATED
204 NO CONTENT
400 BAD REQUEST
401 UNAUTHORIZED
403 FORBIDDEN
404 NOT FOUND
409 CONFLICT
422 UNPROCESSABLE ENTITY
500 INTERNAL SERVER ERROR
```

------------------------------------------------------------------------

# 19. Payment Integration Rules

Payment processing is a critical domain.

The following rules are mandatory:

## 19.1 Never Trust the Client

Do not trust:

-   Payment status from frontend.
-   Amount from frontend.
-   Transaction success from frontend.

The backend MUST verify payment information from the trusted payment
provider.

## 19.2 Webhook Must Be Idempotent

The same webhook may be delivered multiple times.

The system MUST prevent:

-   Duplicate payment records.
-   Duplicate invoice updates.
-   Duplicate inventory deduction.

Use a unique transaction identifier.

Example:

``` python
class PaymentTransaction(models.Model):
    transaction_id = models.CharField(
        max_length=255,
        unique=True,
    )
```

## 19.3 Validate Payment Amount

The received amount MUST match the expected amount.

``` text
Expected: 500,000
Received: 500,000
=> Valid
```

If the amount does not match:

``` text
=> Do not mark invoice as PAID
```

## 19.4 Webhook Flow

``` text
Receive Webhook
      ↓
Validate Payload
      ↓
Verify Signature / Token
      ↓
Check Duplicate Transaction
      ↓
Validate Amount
      ↓
Find Invoice
      ↓
Update Payment
      ↓
Update Invoice
      ↓
Update Inventory
      ↓
Create Audit Log
```

------------------------------------------------------------------------

# 20. AI Integration Rules

AI MUST be treated as an external unreliable service.

The system MUST handle:

-   Timeout.
-   Rate limit.
-   Invalid response.
-   Provider failure.
-   Token limits.

AI responses MUST NOT directly modify critical business data without
validation.

Bad:

``` text
AI says stock = 100
↓
Automatically update database
```

Good:

``` text
AI analyzes data
↓
Returns recommendation
↓
Human reviews
↓
Business action
```

AI prompts SHOULD be versioned and maintained separately.

Example:

``` text
apps/ai_insight/prompts/
├── revenue_analysis.txt
├── product_analysis.txt
└── inventory_recommendation.txt
```

Never expose API keys in source code.

------------------------------------------------------------------------

# 21. Cache Rules

Redis SHOULD be used only when there is a clear caching requirement.

Good candidates:

-   Report results.
-   Frequently accessed configuration.
-   Temporary OTP/session data.
-   Rate limiting.

Do not cache data blindly.

After updating source data, invalidate affected cache entries.

------------------------------------------------------------------------

# 22. Cloudflare R2 / File Storage

Files SHOULD NOT be stored directly in the application container.

Use object storage for:

-   Product images.
-   Customer attachments.
-   Reports.
-   Documents.

Never store secret credentials in code.

Use environment variables.

------------------------------------------------------------------------

# 23. Environment Variables

All environment-specific configuration MUST be externalized.

Bad:

``` python
SECRET_KEY = "my-secret-key"
```

Good:

``` python
SECRET_KEY = os.environ["SECRET_KEY"]
```

Required secrets include:

``` text
SECRET_KEY
DATABASE_PASSWORD
JWT_SECRET
SEPAY_API_KEY
SEPAY_WEBHOOK_SECRET
GEMINI_API_KEY
```

`.env` MUST NOT be committed.

`.env.example` MUST be committed.

------------------------------------------------------------------------

# 24. Security

Mandatory rules:

-   Never commit secrets.
-   Never log passwords or tokens.
-   Validate all input.
-   Use Django password hashing.
-   Use HTTPS in production.
-   Configure CORS carefully.
-   Configure CSRF appropriately.
-   Apply authentication and permission checks.
-   Do not expose internal stack traces in production.
-   Validate webhook authenticity.
-   Apply rate limiting to sensitive endpoints.

------------------------------------------------------------------------

# 25. Testing

Every important business rule MUST have tests.

Minimum test areas:

``` text
Authentication
User Permissions
Customer
Product
Inventory
Invoice
Payment
Webhook
AI Failure Handling
```

## Test Naming

Use descriptive names:

``` python
def test_payment_webhook_should_not_process_duplicate_transaction():
    ...
```

Avoid:

``` python
def test_payment_1():
    ...
```

## Arrange / Act / Assert

Tests SHOULD follow:

``` python
def test_invoice_should_be_paid_after_successful_payment():
    # Arrange
    invoice = create_invoice()

    # Act
    PaymentService.confirm_payment(invoice=invoice)

    # Assert
    assert invoice.status == InvoiceStatus.PAID
```

------------------------------------------------------------------------

# 26. Git Convention

## Branches

Use:

``` text
main
develop
feature/*
bugfix/*
hotfix/*
```

Examples:

``` text
feature/payment-sepay-webhook
feature/invoice-management
bugfix/duplicate-payment
hotfix/payment-production-error
```

## Commit Convention

Use Conventional Commits.

Format:

``` text
<type>(<scope>): <description>
```

Examples:

``` text
feat(payment): add SePay webhook handler

feat(invoice): add invoice creation flow

fix(payment): prevent duplicate webhook processing

refactor(inventory): move stock deduction to service layer

test(payment): add webhook idempotency tests

docs(readme): update setup instructions

chore(deps): update Django version
```

Allowed types:

``` text
feat
fix
refactor
test
docs
chore
perf
ci
build
```

Commits SHOULD be:

-   Small.
-   Focused.
-   Atomic.
-   Easy to review.

Avoid:

``` text
update code
fix
changes
final
```

------------------------------------------------------------------------

# 27. Pull Request Rules

Every PR SHOULD contain:

``` text
## Summary

What was changed?

## Business Requirement

What problem does this solve?

## Technical Changes

What code was changed?

## Testing

How was it tested?

## Risks

Any potential side effects?

## Checklist

- [ ] Code formatted
- [ ] Lint passed
- [ ] Tests passed
- [ ] Migration checked
- [ ] Documentation updated
```

A PR MUST NOT contain:

-   Debug code.
-   Hardcoded secrets.
-   Unused imports.
-   Unnecessary commented-out code.
-   Temporary files.

------------------------------------------------------------------------

# 28. Database Migration Rules

Before creating a migration:

``` bash
python manage.py makemigrations
```

Review the migration.

Then:

``` bash
python manage.py migrate
```

Never manually modify an already-applied migration in shared
environments.

If a schema change is required:

``` text
Create a new migration
```

Do not delete migration history casually.

------------------------------------------------------------------------

# 29. API Documentation

All public APIs SHOULD be documented.

Documentation SHOULD include:

-   Endpoint.
-   HTTP method.
-   Authentication.
-   Request parameters.
-   Request body.
-   Response.
-   Error response.
-   HTTP status code.

Recommended:

``` text
OpenAPI / Swagger
```

------------------------------------------------------------------------

# 30. AI Coding Assistant Rules

AI-generated code MUST follow this document.

Before generating code, AI MUST:

1.  Understand the existing project structure.
2.  Check existing models and services.
3.  Reuse existing utilities.
4.  Avoid duplicating business logic.
5.  Follow naming conventions.
6.  Use type hints where appropriate.
7.  Add or update tests.
8.  Avoid introducing unnecessary dependencies.
9.  Avoid changing unrelated files.
10. Explain migration and database impact.

AI MUST NOT:

-   Invent existing APIs.
-   Invent database fields without checking the model.
-   Hardcode secrets.
-   Add unnecessary architecture.
-   Create duplicate services.
-   Modify unrelated modules.
-   Ignore existing project conventions.

For a new feature, AI SHOULD follow:

``` text
Requirement
    ↓
Existing Code Analysis
    ↓
Database Impact
    ↓
API Design
    ↓
Service Logic
    ↓
Validation
    ↓
Testing
    ↓
Documentation
```

------------------------------------------------------------------------

# 31. Recommended AI Task Format

When requesting code from an AI assistant, provide:

``` text
## Feature

[Feature description]

## Business Rules

[Rules]

## Existing Context

[Existing models/services]

## Expected Output

[Expected API or behavior]

## Constraints

[Technical constraints]

## Testing Requirements

[Test cases]
```

The AI MUST preserve existing architecture unless a refactor is
explicitly requested.

------------------------------------------------------------------------

# 32. Code Review Checklist

Before merging code, review:

## Functionality

-   Does the feature satisfy the requirement?
-   Are edge cases handled?
-   Are business rules correct?

## Code Quality

-   Is the code readable?
-   Are names meaningful?
-   Is logic duplicated?
-   Is the function too complex?

## Django

-   Are queries optimized?
-   Is `select_related` or `prefetch_related` needed?
-   Are migrations safe?
-   Are transactions required?

## Security

-   Are secrets protected?
-   Is authorization enforced?
-   Is input validated?
-   Is sensitive data excluded from logs?

## Testing

-   Are happy paths tested?
-   Are failure cases tested?
-   Are duplicate requests tested?
-   Are payment edge cases tested?

------------------------------------------------------------------------

# 33. Definition of Done

A task is considered DONE only when:

-   [ ] Business requirement is implemented.
-   [ ] Code follows this convention.
-   [ ] Code is formatted.
-   [ ] Lint passes.
-   [ ] Tests are written or updated.
-   [ ] Tests pass.
-   [ ] Database migrations are reviewed.
-   [ ] API documentation is updated if needed.
-   [ ] No secrets are committed.
-   [ ] No debug code remains.
-   [ ] Code review is completed.
-   [ ] Feature is demonstrated successfully.

------------------------------------------------------------------------

# 34. Final Principle

> Write code that another developer can understand six months later.

The best code is not the shortest code.

The best code is:

``` text
Readable
Predictable
Testable
Maintainable
Secure
Consistent
```

This coding convention is mandatory for all new code in the POS
Management System.
