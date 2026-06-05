"""Cliente LLM — agora baseado em Google Gemini.

Mantemos o nome do pacote (`claude_agent`) e o alias `ClaudeClient` para que os
demais módulos (parser, classifier, scorer, personalize) continuem funcionando
sem alteração. Toda a chamada interna agora vai pra API do Gemini.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


@dataclass
class _Stats:
    hits: int = 0
    misses: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cached_tokens: int = 0
    extras: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, int]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cached_tokens": self.total_cached_tokens,
        }


class _ResponseShim:
    """Envelopa a resposta do Gemini num formato parecido com a do Anthropic.

    Mantém atributos `.content[0].text` e `.usage` para preservar compatibilidade
    com chamadores antigos.
    """

    def __init__(self, response):
        self._response = response

    @property
    def text(self) -> str:
        return self._response.text or ""

    @property
    def content(self) -> list[Any]:
        # Replica o shape `response.content[0].text` da SDK Anthropic
        class _Part:
            def __init__(self, text):
                self.text = text

        return [_Part(self._response.text or "")]

    @property
    def usage(self):
        return self._response.usage_metadata


class GeminiClient:
    """Wrapper Gemini com a mesma assinatura externa do antigo ClaudeClient.

    Métodos públicos:
    - call(prompt, system, temperature, ...) -> resposta
    - extract_json(prompt, system, schema_hint) -> dict
    - stats() -> dict de uso
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
    ):
        api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY não definida. Configure no .env ou passe como parâmetro."
            )

        self.client = genai.Client(api_key=api_key)
        self.model = model or os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
        self.max_tokens = int(max_tokens or os.environ.get("GEMINI_MAX_TOKENS", "4096"))
        self._stats = _Stats()

    # ====== API pública ======

    def call(
        self,
        prompt: str,
        system: str | None = None,
        cache_system: bool = False,  # mantido por compat — Gemini cache é diferente
        temperature: float = 0.0,
        tools: list[dict] | None = None,
        response_mime_type: str | None = None,
    ) -> _ResponseShim:
        """Chama Gemini e devolve resposta envelopada (parece Anthropic)."""

        cfg_kwargs: dict[str, Any] = {
            "temperature": temperature,
            "max_output_tokens": self.max_tokens,
        }
        if system:
            cfg_kwargs["system_instruction"] = system
        if response_mime_type:
            cfg_kwargs["response_mime_type"] = response_mime_type

        # Desabilita thinking budget no 2.5-flash para liberar tokens para a saída
        # (thinking consome max_output_tokens antes da resposta efetiva)
        if "2.5-flash" in self.model or "2.5-pro" in self.model:
            try:
                cfg_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
            except Exception:
                pass

        response = None
        for attempt in range(3):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(**cfg_kwargs),
                )
                break
            except Exception as e:
                msg = str(e).lower()
                transient = any(s in msg for s in (
                    "429", "rate", "quota", "resource_exhausted", "503", "overload",
                    "unavailable", "timeout", "deadline", "500", "internal",
                ))
                if attempt < 2 and transient:
                    wait = 1.5 * (2 ** attempt)
                    logger.warning("Gemini transitório (tentativa %d/3): %s — retry em %.1fs", attempt + 1, e, wait)
                    time.sleep(wait)
                    continue
                logger.error("Falha na chamada Gemini: %s", e)
                raise

        # Atualiza stats
        usage = getattr(response, "usage_metadata", None)
        if usage:
            self._stats.total_input_tokens += getattr(usage, "prompt_token_count", 0) or 0
            self._stats.total_output_tokens += getattr(usage, "candidates_token_count", 0) or 0
            cached = getattr(usage, "cached_content_token_count", 0) or 0
            self._stats.total_cached_tokens += cached
            if cached > 0:
                self._stats.hits += 1
            else:
                self._stats.misses += 1
        else:
            self._stats.misses += 1

        return _ResponseShim(response)

    def extract_json(
        self,
        prompt: str,
        system: str | None = None,
        schema_hint: str = "",
    ) -> dict[str, Any]:
        """Pede ao Gemini retorno em JSON e faz parse defensivo."""
        full_prompt = prompt
        if schema_hint:
            full_prompt += f"\n\nResponda APENAS com JSON válido seguindo esse formato:\n{schema_hint}"
        else:
            full_prompt += "\n\nResponda APENAS com JSON válido, sem comentários, sem markdown."

        # Gemini suporta forçar JSON via response_mime_type
        response = self.call(
            full_prompt,
            system=system,
            temperature=0.0,
            response_mime_type="application/json",
        )
        text = (response.content[0].text or "").strip()

        # Remove cercas de markdown se Gemini incluir mesmo assim
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:].strip()
            text = text.rstrip("`").strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error("Falha ao parsear JSON do Gemini: %s\nTexto: %s", e, text[:500])
            raise

    def call_with_files(self, prompt: str, files: list[tuple[bytes, str]], system: str | None = None) -> "_ResponseShim":
        """Como call(), mas anexa arquivos (Gemini lê PDF/imagens nativamente).

        files: lista de (bytes, mime_type). Força saída JSON (application/json).
        """
        parts: list[Any] = []
        for data, mime in files:
            try:
                parts.append(types.Part.from_bytes(data=data, mime_type=mime))
            except Exception as e:  # anexo problemático não derruba a anamnese
                logger.warning("Anexo ignorado (%s): %s", mime, e)
        parts.append(types.Part.from_text(text=prompt))

        cfg_kwargs: dict[str, Any] = {
            "temperature": 0.0,
            "max_output_tokens": self.max_tokens,
            "response_mime_type": "application/json",
        }
        if system:
            cfg_kwargs["system_instruction"] = system
        if "2.5-flash" in self.model or "2.5-pro" in self.model:
            try:
                cfg_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
            except Exception:
                pass

        response = self.client.models.generate_content(
            model=self.model,
            contents=parts,
            config=types.GenerateContentConfig(**cfg_kwargs),
        )
        return _ResponseShim(response)

    def stats(self) -> dict[str, int]:
        return self._stats.as_dict()


# ====== Alias de compatibilidade ======
# O resto do código importa `ClaudeClient`. Mantemos o nome.
ClaudeClient = GeminiClient
