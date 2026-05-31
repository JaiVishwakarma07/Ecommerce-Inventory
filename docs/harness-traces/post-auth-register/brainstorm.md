# Brainstorm: POST /auth/register

## Task

Implement `POST /auth/register` as a focused vertical slice, based on:
- `specs/user-authentication/spec.md`
- `specs/user-authentication/plan.md`

## Final Decisions

- Canonical route: `POST /auth/register`
- Request payload from frontend: `{ email, full_name, password }`
- Response shape stays plain (no envelope for now):
  `{ access_token, token_type, user }`
- Self-registration always forces `role="customer"`
- Any incoming role intent from client is ignored

## Architecture (Approved)

Implement one endpoint-focused layered flow:

- **Route** (`app/api/routes/auth.py`)
  - Validate incoming schema
  - Call service for registration
  - Return plain response payload

- **Service** (`app/services/auth_service.py`)
  - Normalize email
  - Check duplicate email
  - Hash password
  - Create user with forced `customer` role
  - Issue 24h JWT access token
  - Build response DTO

- **Repository** (`app/repositories/user_repository.py`)
  - Async DB operations (`get_by_email`, `create`)

- **Model** (`app/models/user.py`)
  - Persistent `User` entity

- **Security helpers** (`app/core/security.py`)
  - bcrypt hash/verify
  - JWT create/verify (python-jose)

## Data Flow (Approved)

1. Receive `{ email, full_name, password }`
2. Validate request payload
3. Normalize email (`trim + lowercase`)
4. Query existing user by email
5. If exists -> return `409`
6. Hash password with bcrypt
7. Persist user with role forced to `customer`
8. Issue 24-hour bearer token
9. Return `{ access_token, token_type, user }`

## Error Contract (Approved)

- `200`: register success
- `400`: validation failure
- `409`: duplicate email
- `500`: internal error (sanitized)

Security constraints:
- Never return password/password_hash
- Never log raw password
- JWT secret sourced from environment config

## Testing Strategy (Approved)

### Contract Tests

- Register accepts only `{ email, full_name, password }`
- Response includes `access_token`, `token_type`, and `user`
- Response excludes password fields

### Integration Tests

- Success registration returns `200` and valid payload
- Duplicate registration returns `409`
- Invalid payload returns `400`

### Unit Tests

- Password hashing/verification behavior
- JWT issuance with expected subject/expiry intent
- Service enforces role = `customer`

## Observability Requirements (Approved)

Structured logs for register attempts:
- `request_id`, `path`, `method`, `status_code`, `latency_ms`
- `user_id` only on success

Metrics:
- `auth_register_total{status="success|conflict|validation_error|error"}`

No secrets in logs:
- No password, password hash, or secret values in log context

## Acceptance Criteria

- Endpoint implemented at `POST /auth/register`
- Request contract is exactly `{ email, full_name, password }`
- Role is always persisted as `customer` on self-registration
- Response remains plain payload format
- Tests and error behavior match approved contract
- Observability hooks present for register path
