---
description: "Task list for user authentication implementation"
---

# Tasks: User Authentication

**Input**: Design documents from `specs/user-authentication/`

**Prerequisites**: `plan.md` (required), `spec.md` (required), `contracts/` (available)

**Tests**: Test tasks are REQUIRED for every user story. Follow TDD: write tests first, confirm they fail, then implement.

**Organization**: Tasks are grouped by user story so each story can be built and tested independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Parallelizable task (different files, no dependency on unfinished tasks)
- **[Story]**: User story label for story-specific phases (`[US1]`, `[US2]`, `[US3]`)
- Include exact file paths in each task

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialize project skeleton, dependencies, and baseline app wiring.

- [ ] T001 Create backend package structure in `app/` and `tests/` with `__init__.py` files
- [ ] T002 Add required auth/database/testing dependencies in `pyproject.toml` or `requirements.txt`
- [ ] T003 [P] Configure environment settings loader in `app/core/config.py`
- [ ] T004 [P] Configure async DB engine/session factory in `app/db/session.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build shared primitives that all user stories depend on.

**⚠️ CRITICAL**: User story implementation starts only after this phase completes.

- [ ] T005 Create SQLAlchemy base and `User` model in `app/models/user.py`
- [ ] T006 Add users table migration in `alembic/versions/20260526_create_users_table.py`
- [ ] T007 [P] Implement user repository methods in `app/repositories/user_repository.py`
- [ ] T008 [P] Implement bcrypt and JWT helpers in `app/core/security.py`
- [ ] T009 [P] Add auth schemas in `app/schemas/auth.py`
- [ ] T010 [P] Define auth API contract baseline in `specs/user-authentication/contracts/auth-api.yaml`
- [ ] T011 Create FastAPI app shell and root route in `app/main.py`

**Checkpoint**: Foundations complete; user stories can proceed.

---

## Phase 3: User Story 1 - Register Account (Priority: P1) 🎯 MVP

**Goal**: User can register with email/password/full_name and receive access token.

**Independent Test**: `POST /auth/register` returns `{access_token, token_type, user}` and duplicate email returns `409`.

### Tests for User Story 1 (REQUIRED) ⚠️

- [ ] T012 [P] [US1] Write failing contract test for register response shape in `tests/contract/test_auth_contract.py`
- [ ] T013 [P] [US1] Write failing integration tests for register success and duplicate email in `tests/integration/test_auth_endpoints.py`
- [ ] T014 [US1] Run US1 tests and confirm failures with `pytest tests/contract/test_auth_contract.py tests/integration/test_auth_endpoints.py -k register -v`

### Implementation for User Story 1

- [ ] T015 [US1] Implement register service flow in `app/services/auth_service.py`
- [ ] T016 [US1] Implement `POST /auth/register` route in `app/api/routes/auth.py`
- [ ] T017 [US1] Register auth router in `app/main.py`
- [ ] T018 [US1] Re-run US1 tests and confirm pass with `pytest tests/contract/test_auth_contract.py tests/integration/test_auth_endpoints.py -k register -v`

**Checkpoint**: Register flow is independently functional and testable.

---

## Phase 4: User Story 2 - Login and Current User (Priority: P1)

**Goal**: User can login and retrieve profile using bearer token.

**Independent Test**: `POST /auth/login` returns token and `GET /auth/me` returns user profile with valid token.

### Tests for User Story 2 (REQUIRED) ⚠️

- [ ] T019 [P] [US2] Write failing contract tests for login and me responses in `tests/contract/test_auth_contract.py`
- [ ] T020 [P] [US2] Write failing integration tests for login success/failure and me auth in `tests/integration/test_auth_endpoints.py`
- [ ] T021 [US2] Run US2 tests and confirm failures with `pytest tests/contract/test_auth_contract.py tests/integration/test_auth_endpoints.py -k "login or me" -v`

### Implementation for User Story 2

- [ ] T022 [US2] Implement login service flow in `app/services/auth_service.py`
- [ ] T023 [US2] Implement token auth dependency in `app/api/deps/auth.py`
- [ ] T024 [US2] Implement `POST /auth/login`, `POST /auth/login-form`, and `GET /auth/me` in `app/api/routes/auth.py`
- [ ] T025 [US2] Re-run US2 tests and confirm pass with `pytest tests/contract/test_auth_contract.py tests/integration/test_auth_endpoints.py -k "login or me" -v`

**Checkpoint**: Login + me flows are independently functional and testable.

---

## Phase 5: User Story 3 - Security Policy and Observability (Priority: P2)

**Goal**: Enforce public allowlist/default-protected routes and emit structured auth telemetry.

**Independent Test**: Public routes are accessible without token; non-allowlisted routes require auth; auth endpoints emit expected log/metric hooks.

### Tests for User Story 3 (REQUIRED) ⚠️

- [ ] T026 [P] [US3] Write failing route access policy tests in `tests/contract/test_route_access_policy.py`
- [ ] T027 [P] [US3] Write failing auth observability unit tests in `tests/unit/test_auth_dependencies.py`
- [ ] T028 [US3] Run US3 tests and confirm failures with `pytest tests/contract/test_route_access_policy.py tests/unit/test_auth_dependencies.py -v`

### Implementation for User Story 3

- [ ] T029 [US3] Implement structured auth logging/metrics helpers in `app/core/observability.py`
- [ ] T030 [US3] Implement route public allowlist/default-protect policy in `app/main.py`
- [ ] T031 [US3] Wire observability hooks into auth flows in `app/api/routes/auth.py` and `app/api/deps/auth.py`
- [ ] T032 [US3] Update API contract auth/public annotations in `specs/user-authentication/contracts/auth-api.yaml`
- [ ] T033 [US3] Re-run US3 tests and confirm pass with `pytest tests/contract/test_route_access_policy.py tests/unit/test_auth_dependencies.py -v`

**Checkpoint**: Security defaults and observability are independently testable.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final hardening, documentation consistency, and full-suite verification.

- [ ] T034 [P] Add token-expiry and invalid-token edge-case tests in `tests/unit/test_security.py`
- [ ] T035 [P] Add role restriction integration test (`403`) in `tests/integration/test_auth_endpoints.py`
- [ ] T036 Update API contract draft annotations in `docs/design/api-contract-draft.md`
- [ ] T037 Run complete test suite with `pytest tests/unit tests/integration tests/contract -v`
- [ ] T038 Validate local runbook steps in `specs/user-authentication/plan.md` quickstart section

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: Starts immediately.
- **Phase 2 (Foundational)**: Depends on Phase 1 completion.
- **Phase 3 (US1)**: Depends on Phase 2 completion.
- **Phase 4 (US2)**: Depends on Phase 2 completion; can start after US1 model/service primitives are stable.
- **Phase 5 (US3)**: Depends on Phase 4 auth flow implementation.
- **Phase 6 (Polish)**: Depends on completion of selected user stories.

### User Story Dependencies

- **US1 (P1)**: No dependency on other stories after foundational phase.
- **US2 (P1)**: Depends on core user entity and security primitives; functionally extends US1.
- **US3 (P2)**: Depends on US1+US2 endpoints existing for policy and observability validation.

### Within Each User Story

- Tests must be written and FAIL before implementation.
- Contract updates happen before or with endpoint implementation.
- Service logic before route wiring.
- Route implementation before integration assertions pass.

### Parallel Opportunities

- Phase 1: T003 and T004 can run in parallel.
- Phase 2: T007, T008, T009, T010 can run in parallel.
- US1: T012 and T013 can run in parallel.
- US2: T019 and T020 can run in parallel.
- US3: T026 and T027 can run in parallel.
- Phase 6: T034 and T035 can run in parallel.

---

## Parallel Execution Examples

### User Story 1

```bash
Task: "T012 [US1] contract test for register response shape in tests/contract/test_auth_contract.py"
Task: "T013 [US1] integration tests for register success and duplicate email in tests/integration/test_auth_endpoints.py"
```

### User Story 2

```bash
Task: "T019 [US2] contract tests for login and me responses in tests/contract/test_auth_contract.py"
Task: "T020 [US2] integration tests for login success/failure and me auth in tests/integration/test_auth_endpoints.py"
```

### User Story 3

```bash
Task: "T026 [US3] route access policy tests in tests/contract/test_route_access_policy.py"
Task: "T027 [US3] auth observability tests in tests/unit/test_auth_dependencies.py"
```

---

## Implementation Strategy

### MVP First (US1)

1. Complete Phase 1 and Phase 2.
2. Complete Phase 3 (US1) only.
3. Validate register contract + integration tests.
4. Demo register-only auth bootstrap.

### Incremental Delivery

1. Deliver US1 (register).
2. Deliver US2 (login + me).
3. Deliver US3 (security defaults + observability).
4. Finish with Phase 6 hardening.

### Suggested MVP Scope

- MVP = **User Story 1** (`register`) on top of foundational phases.
