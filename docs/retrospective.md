# Retrospective — ECOM_OPPO Inventory Project

**Author:** Developer (solo build, AI-assisted)  
**Scope:** FastAPI backend + React/Vite frontend, auth, catalog, orders/checkout  
**Harness:** ECC + GitHub Spec Kit + OpenSpec + Superpowers (via Cursor)  
**Period:** May 2026

This retrospective is honest about where AI helped, where it wasted time, and where I had to intervene manually.

---

## 1. Process

### Where AI clearly boosted productivity

**Spec and contract drafting (early feature work)**  
For orders/checkout, AI was fastest when turning a fuzzy requirement (“checkout must snapshot prices and decrement stock atomically”) into concrete artifacts: `specs/003-orders-checkout/spec.md`, `contracts/orders-api.yaml`, and pytest contract tests. That cut what would have been a half-day of typing into roughly an hour of review and correction.

**Backend implementation scaffolding**  
Layered FastAPI structure (routers → services → repositories) repeated across auth, products, and orders. AI generated consistent patterns — `require_admin`, `require_customer`, Pydantic schemas, async SQLAlchemy repos — so the second and third features moved faster than the first. The product catalog integration tests were largely AI-drafted and needed only small fixes for SKU uniqueness edge cases.

**Documentation and diagrams**  
`docs/architecture.md` mermaid flows and the API overview tables were generated quickly and were actually useful for onboarding myself after a break. Updating harness trace docs (`docs/harness-traces/*/verify-output.md`) after test runs was tedious but AI made it bearable.

**Frontend utility tests (late project)**  
Pure functions (`validateCartStock`, `formatApiError`, `toProductWrite`) were ideal AI test targets. Getting 42 utility and component tests in place in one session — after Vitest config was sorted — was genuinely faster than writing them by hand.

### Where AI slowed me down

**Over-process for small tasks**  
The harness mandates Brainstorm → Plan → Implement → Verify for *everything*. Fixing a typo in a quickstart doc or updating a seed script comment still triggered skills checks and trace expectations. Correct for feature work, but heavy for chores that did not touch behaviour.

**Test infrastructure rabbit holes**  
Setting up Vitest with tests living in `tests/frontend/` (outside `frontend/node_modules`) cost ~45 minutes of failed runs: setup file resolution, `react/jsx-dev-runtime` alias issues, and wrong expected values in `buildInsights.test.js` (I had miscalculated inventory value as ₹1,250; actual was ₹1,425). AI initially asserted tests passed before the config was fixed — I learned to distrust summary claims without reading exit codes.

**Stale documentation drift**  
`docs/architecture.md` still labelled orders modules as “(planned)” long after `backend/app/routers/orders.py` shipped. AI had generated the doc from an older plan snapshot and I did not reconcile it until I noticed the mismatch while writing frontend tests. That created a false picture of project completeness for anyone reading docs before code.

**Duplicate implementation attempts**  
During product catalog work, AI once proposed a separate `/api/v1/products` router while the approved spec and React client both used bare `/products` on `VITE_API_URL`. I caught it in review, but only because the contract test file was already open — otherwise I would have shipped incompatible routes.

---

## 2. Harness & Skills

### Why this harness

I chose **ECC + Spec Kit + OpenSpec + Superpowers** because the project was spec-driven from the start: feature folders under `specs/`, OpenAPI contracts, and explicit user stories (admin CRUD, customer checkout, cancel restock). Cursor’s `.cursor/rules` and skills gave repeatable prompts so I did not re-explain “async SQLAlchemy only, no passwords in responses” every session.

Spec Kit’s `.specify/` scripts (`check-prerequisites.sh`, feature branch detection) anchored planning to `specs/<feature>/plan.md` and `tasks.md`. OpenSpec’s `openspec/changes/` gave a paper trail for auth persistence and login integration without mixing them into unrelated specs.

### Phase value vs redundancy


| Phase          | Value                         | Notes                                                                                                                            |
| -------------- | ----------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| **Brainstorm** | **High** for orders           | Forced explicit decisions: line-item snapshots, no FK on `product_id`, one-time cancel restock. Avoided a bad normalized schema. |
| **Plan**       | **High** for backend features | Step-by-step TDD plans in `specs/*/plan.md` matched how I actually implemented.                                                  |
| **Implement**  | **Mixed**                     | Great for boilerplate; sometimes AI skipped reading existing code and duplicated helpers.                                        |
| **Verify**     | **High**                      | `docs/harness-traces/*/verify-output.md` with real pytest output caught regressions. Non-negotiable.                             |


**Most redundant:** Running the full Superpowers cycle (brainstorm + writing-plans + TDD skill invocation) for **documentation-only** work — e.g. refreshing README setup steps or editing harness trace summaries after a passing test run. The skills added ceremony without new technical risk. A lighter “docs mode” would have saved an hour.

**Second redundancy:** Parallel planning artifacts — `docs/superpowers/specs/`, `specs/*/plan.md`, and `openspec/changes/*/design.md` sometimes repeated the same checkout transaction rules in three places. One source of truth would suffice; I maintained three because the harness expected them.

---

## 3. AI Collaboration

### “AI saved the day” — orders checkout transaction

The most valuable moment was designing **checkout as a single database transaction**: merge duplicate cart lines, validate stock, snapshot `product_name` and `unit_price`, insert order + line items, decrement inventory. I was going to split this into “create order” then “adjust stock” as two service calls. AI’s brainstorm doc (`docs/superpowers/specs/2026-05-28-orders-checkout-design.md`) argued for one transaction with `ProductRepository.adjust_quantity` flushing but not committing — which matched how SQLAlchemy sessions already worked in the repo. That prevented a real production bug (order created, stock not decremented on mid-flight failure).

Contract tests AI drafted (`tests/contract/test_orders_contract.py`) also locked the frontend expectation that routes live at `/orders`, not `/api/v1/orders` — matching `VITE_API_URL` usage in the React client.

### “AI led me astray” — required

**The failure:** While implementing admin authorization, AI suggested reading `role` directly from the JWT payload to gate `POST /products` and order admin routes — faster than a database lookup on every request. I almost merged it. The existing pattern in `backend/app/dependencies/auth.py` loads the user from the DB on each protected call so a demoted admin cannot keep operating until token expiry. JWT-only role checks would have violated that security model and diverged from the integration tests in `tests/integration/test_products.py`, which assume DB-backed roles.

I caught it because the test `test_create_product_requires_admin` failed when I prototyped the JWT shortcut locally. AI had described the approach as “standard JWT practice” without checking our spec or test suite.

**Secondary astray moment:** When adding frontend tests, AI’s first `buildInsights` test expected `inventory_value: 1250` and top product “Gadget.” Running the test showed **1425** and “Widget” (2 units sold). The frontend code was correct; the test expectations were wrong — AI had hand-waved the arithmetic. I fixed the test, not the app, but only because I ran `npm test` and read failures instead of accepting “looks good.”

### How I built a habit of catching wrong AI output

1. **No “done” without a command** — `pytest -q` for backend, `npm test` for frontend. If AI claims success, I ask for the last 20 lines of output or run it myself.
2. **Read one failing test first** — when AI changes auth or routing, I run the narrowest pytest slice (`-k admin` or a single contract file) before trusting the summary.
3. **Read one contract test** — if AI says an endpoint exists, I open `tests/contract/` or hit `/docs` instead of trusting prose.
4. **Smallest diff rule** — when AI proposes wide refactors (e.g. merging auth routers or adding a `/api/v1` prefix everywhere), I reject and ask for the minimal fix aligned with the spec.
5. **Harness verify traces** — saving actual terminal output to `verify-output.md` creates a paper trail AI cannot hallucinate away later.

---

## 4. Reflection

### If I did it again

1. **Tier the harness** — full Brainstorm → Plan → Implement → Verify for features; lightweight path for docs and dependency bumps.
2. **Single planning source** — keep `specs/<feature>/plan.md` authoritative; link OpenSpec/Superpowers docs instead of duplicating transaction rules.
3. **CI from the first merge** — one job for `pytest`, one for `npm test`. Would have caught the 13 pre-existing sync/async unit test errors (`pytest.PytestRemovedIn9Warning` on autouse async fixtures) earlier instead of discovering them in a harness verify log.
4. **Generate architecture from code** — run a checklist after each feature lands so “(planned)” labels do not linger in `docs/architecture.md`.
5. **Frontend tests earlier** — utility tests for `validateCartStock` and `formatApiError` would have been cheap to add right after the cart and register pages shipped, not at the end.

### Scaling to a real team

**What scales well**

- Feature folders in `specs/` with contracts — clear handoff between backend and frontend devs; the React app’s `api/client.js` and bare `/products` paths were already aligned with OpenAPI.
- `.cursor/rules/common/project.mdc` — short, enforceable conventions (async only, no secrets in responses).
- Separate backend (`tests/`) and frontend (`tests/frontend/`) test trees — QA knows where to look; Vitest config stays in `frontend/` without polluting `src/`.

**What does not scale without tuning**

- Four overlapping harness layers confuse newcomers (“Do I run Spec Kit, OpenSpec, or Superpowers first?”).
- Mandatory AI skills for every task inflate PR time if reviewers expect harness trace folders for a typo fix.
- Heavy `.cursor/` skill library (400+ files) is intimidating; teams need a curated subset per stack (FastAPI + React only).
- AI defaults to bash/macOS examples in docs (`source .venv/bin/activate`) — Windows contributors need explicit equivalents in the root README.

**Realistic team model:** Keep spec + contract + verify for features; assign one “harness maintainer” to trim redundancy; use CI as the neutral judge instead of AI self-reporting pass/fail.

---

## Summary

AI materially accelerated spec-driven backend work and frontend utility testing, but it also proposed a weaker JWT-only auth shortcut and produced wrong test expectations until I ran commands locally. The harness paid off on orders/checkout design and verification; it felt redundant on documentation chores. The workflow is viable for a small team if we reduce ceremony on non-feature work and treat **terminal output as the source of truth**, not the model’s closing summary.