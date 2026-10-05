"""
Base agent class for AutoNegocio AI agents.
All agents use the Anthropic Claude API for intelligent decision-making.
"""

import logging
from typing import Optional

from backend.config.settings import settings

logger = logging.getLogger(__name__)


def get_claude_client():
    """Get an Anthropic client instance. Returns None if API key not configured."""
    try:
        import anthropic
        if not settings.ANTHROPIC_API_KEY:
            logger.warning("ANTHROPIC_API_KEY not set — AI agents will use fallback logic")
            return None
        return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    except ImportError:
        logger.warning("anthropic package not installed — AI agents will use fallback logic")
        return None


def ask_claude(prompt: str, system: str = "", max_tokens: int = 1024) -> Optional[str]:
    """
    Send a prompt to Claude and return the text response.
    Returns None if the API is unavailable.
    """
    client = get_claude_client()
    if not client:
        return None

    try:
        messages = [{"role": "user", "content": prompt}]
        kwargs = {
            "model": settings.CLAUDE_MODEL,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system

        response = client.messages.create(**kwargs)
        return response.content[0].text
    except Exception as exc:
        logger.error("Claude API error: %s", exc)
        return None
