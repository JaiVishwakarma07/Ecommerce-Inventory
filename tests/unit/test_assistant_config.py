"""Unit tests for LLM assistant settings (Task 1 — config RED)."""

from __future__ import annotations


def test_settings_reads_llm_env_without_ecom_prefix(monkeypatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
    monkeypatch.setenv("LLM_MODEL", "llama-3.3-70b-versatile")

    from app.config import Settings

    settings = Settings()
    assert settings.llm_api_key == "test-key"
    assert settings.llm_base_url == "https://api.groq.com/openai/v1"
    assert settings.llm_model == "llama-3.3-70b-versatile"
    assert settings.llm_timeout_seconds == 15


def test_settings_llm_configured_when_key_and_base_url_present(monkeypatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "k")
    monkeypatch.setenv("LLM_BASE_URL", "https://example.com/v1")

    from app.config import Settings

    assert Settings().llm_configured is True


def test_settings_llm_not_configured_when_key_missing(monkeypatch) -> None:
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setenv("LLM_BASE_URL", "https://example.com/v1")

    from app.config import Settings

    assert Settings().llm_configured is False
