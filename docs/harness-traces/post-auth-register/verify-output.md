# Verification Output

Task: `post-auth-register`

## Verification command

```bash
PYTHONPATH="backend/.deps:${PYTHONPATH}" pytest tests/integration/test_auth_register.py tests/contract/test_auth_contract.py tests/unit/test_security.py -q
```

## Test run output (latest)

```text
...........                                                              [100%]
=============================== warnings summary ===============================
.deps/passlib/utils/__init__.py:854
  /Users/jaivishwakarma/Documents/Ecom-oppo/.deps/passlib/utils/__init__.py:854: DeprecationWarning: 'crypt' is deprecated and slated for removal in Python 3.13
    from crypt import crypt as _crypt

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
11 passed, 1 warning in 2.97s
```

## Coverage

- **Coverage %:** Not available in current environment (N/A)
- **Reason:** `pytest-cov`/`coverage.py` tooling is not installed and could not be fetched due SSL certificate verification failures during package install.
- **Attempted commands:**
  - `pytest ... --cov=app --cov-report=term-missing` (failed: unrecognized `--cov` args)
  - `coverage run -m pytest ...` (failed: `coverage` command not found)
