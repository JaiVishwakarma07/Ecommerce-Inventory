<!--
Sync Impact Report
- Version change: 1.0.0 -> 2.0.0
- Modified principles:
  - I. Spec-Driven Delivery -> I. API-First Contracts
  - II. Test-First Quality Gates (NON-NEGOTIABLE) -> II. Test-First Delivery (NON-NEGOTIABLE)
  - III. Secure API by Default -> III. Security by Default (Auth-Required)
  - IV. Consistent Contracts and Observability -> IV. Async Throughout
  - V. Immutable, Reviewable Changes -> V. Observability by Default
- Added sections:
  - None
- Removed sections:
  - None (section content amended)
- Templates requiring updates:
  - ✅ .specify/templates/plan-template.md
  - ✅ .specify/templates/tasks-template.md
  - ✅ .specify/templates/spec-template.md (reviewed; no structural change required)
  - ✅ .specify/templates/checklist-template.md (reviewed; no change required)
- Follow-up TODOs:
  - None.
-->
# ECOM_OPPO Constitution

## Core Principles

### I. API-First Contracts
Every feature MUST start with an API contract before implementation begins.
Contracts MUST define endpoint paths, methods, request/response schemas, auth
requirements, and error shapes. Implementation PRs that change behavior without a
corresponding contract update are non-compliant.
Rationale: Contract-first design keeps backend and client expectations aligned and
reduces ambiguity in ecommerce workflows.

### II. Test-First Delivery (NON-NEGOTIABLE)
No implementation may ship without tests. All functional changes MUST follow TDD:
write tests first, confirm failures, implement minimal code, and refactor.
Coverage across unit, integration, and critical endpoint flows MUST remain at or
above 80% before merge or release.
Rationale: Test-first discipline ensures behavior is verified continuously and
prevents regressions in order, catalog, and inventory logic.

### III. Security by Default (Auth-Required)
All endpoints MUST require authentication and authorization unless explicitly marked
public in the API contract. Public endpoints MUST be intentionally listed and
justified. Input validation, secret management, and safe error handling are
mandatory at all API boundaries.
Rationale: Default-deny access control minimizes accidental exposure and enforces a
clear trust model.

### IV. Async Throughout
The service MUST be asynchronous end-to-end. Blocking I/O is prohibited in request
handlers, dependencies, and data-access paths. Any unavoidable sync integration
MUST be isolated and explicitly justified with a non-blocking strategy.
Rationale: Async-only execution preserves throughput and latency under concurrent
ecommerce traffic.

### V. Observability by Default
Every endpoint MUST emit structured logs and metrics for request lifecycle,
latency, status outcome, and error conditions. Observability instrumentation is a
release gate, not a post-release task.
Rationale: Reliable telemetry is required for incident response, performance tuning,
and operational confidence.

## Engineering Constraints

- Platform scope is a FastAPI REST API for ecommerce inventory management.
- API response formats MUST remain consistent with published contracts.
- Database and external service calls MUST use non-blocking async clients.
- Endpoint-level auth defaults to protected; public routes must be contract-declared.
- Logging/metrics MUST use configured observability tooling; `print()` is prohibited.

## Delivery Workflow and Quality Gates

1. Brainstorm requirements and edge cases before implementation starts.
2. Produce or update API contract, spec, and plan artifacts before coding.
3. Implement via TDD and keep task execution traceable to contract and user stories.
4. Enforce auth defaults, async-only I/O, and observability for every endpoint.
5. Run verification (lint, tests, and contract checks) before completion claims.
6. Request code review after each major implementation step and resolve critical
   findings before merge.
7. Do not commit or create PRs when verification gates are failing.

## Governance

This constitution supersedes conflicting local conventions in this repository.
Amendments require: (1) documented rationale, (2) updates to impacted templates and
guidance files, and (3) a semantic version decision with justification.

Versioning policy:
- MAJOR: Removes or redefines a principle in a backward-incompatible way.
- MINOR: Adds a new principle/mandatory section or materially expands obligations.
- PATCH: Clarifies wording, fixes typos, or improves guidance without changing
  obligations.

Compliance review expectations:
- Every plan MUST include a Constitution Check against active principles.
- Every tasks artifact MUST include contract-first, test-first, auth-default,
  async, and observability work items.
- Reviewers MUST block merges that violate non-negotiable principles.

**Version**: 2.0.0 | **Ratified**: 2026-05-26 | **Last Amended**: 2026-05-26
