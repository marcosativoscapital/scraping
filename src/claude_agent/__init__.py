"""Integração com LLM para parsing, classificação, scoring e personalização.

Backend atual: Google Gemini (substituiu o Claude em 2026-05-28).
O pacote mantém o nome `claude_agent` por compatibilidade com chamadores existentes.
"""

from .client import ClaudeClient, GeminiClient

__all__ = ["ClaudeClient", "GeminiClient"]
