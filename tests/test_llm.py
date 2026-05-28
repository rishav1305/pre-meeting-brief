from unittest.mock import patch, MagicMock
import api.llm as llm


def test_get_client_passes_api_key():
    with patch("api.llm.Anthropic") as MockAnthropic:
        llm.get_client()
        # The settings.anthropic_api_key value is loaded from .env.local — just verify it's passed
        call_kwargs = MockAnthropic.call_args.kwargs
        assert "api_key" in call_kwargs
        assert call_kwargs["api_key"]  # non-empty


def test_get_client_passes_base_url_when_set():
    with patch("api.llm.Anthropic") as MockAnthropic, \
         patch("api.llm.settings") as mock_settings:
        mock_settings.anthropic_api_key = "test-key"
        mock_settings.anthropic_base_url = "https://proxy.example/litellm"
        llm.get_client()
        assert MockAnthropic.call_args.kwargs["base_url"] == "https://proxy.example/litellm"


def test_get_client_omits_base_url_when_unset():
    with patch("api.llm.Anthropic") as MockAnthropic, \
         patch("api.llm.settings") as mock_settings:
        mock_settings.anthropic_api_key = "test-key"
        mock_settings.anthropic_base_url = ""
        llm.get_client()
        assert "base_url" not in MockAnthropic.call_args.kwargs
