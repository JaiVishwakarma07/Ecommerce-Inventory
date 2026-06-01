# Verification Output

Task: `004-ai-shopping-assistant`

## Verification command

```bash
PYTHONPATH=backend python -m pytest \
  tests/unit/test_assistant_config.py \
  tests/unit/test_assistant_answer.py \
  tests/unit/test_assistant_repository.py \
  tests/unit/test_assistant_llm_client.py \
  tests/unit/test_assistant_service.py \
  tests/integration/test_assistant.py \
  tests/contract/test_assistant_contract.py \
  tests/contract/test_route_access_policy.py::test_post_assistant_query_requires_authentication \
  tests/integration/test_auth_login.py \
  tests/integration/test_products.py \
  -q --asyncio-mode=auto
```

## Test run output (2026-06-01)

```text
72 passed, 8 warnings in 11.48s
```

## Frontend manual checklist (T032)

- [ ] Login as customer → `/products` shows Ask AI form
- [ ] Logout → Ask AI hidden
- [ ] Login as admin → Ask AI hidden
- [ ] Customer submits query with `LLM_*` env set → answer + product cards render

## Notes

- Integration tests mock LLM via FastAPI `app.dependency_overrides[get_llm_client]`
- Live Groq requires `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` in `backend/.env`
