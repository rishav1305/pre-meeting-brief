"""Anthropic client factory configured for the LiteLLM proxy.

Both ANTHROPIC_API_KEY and ANTHROPIC_BASE_URL are loaded from settings.
When base_url is unset, the SDK uses Anthropic's default endpoint.
When set (production), all requests route through api.mercury.weather.com/litellm.
"""
from anthropic import Anthropic

from api.config import settings


DEFAULT_MODEL = "claude-sonnet-4-6"  # synthesis + research
CHEAP_MODEL = "claude-haiku-4-5"      # qualification + DQ tie-breaks


def get_client() -> Anthropic:
    kwargs: dict = {"api_key": settings.anthropic_api_key}
    if settings.anthropic_base_url:
        kwargs["base_url"] = settings.anthropic_base_url
    return Anthropic(**kwargs)
