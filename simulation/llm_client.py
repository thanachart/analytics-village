"""
Analytics Village — Ollama LLM Client.
Wraps the openai SDK pointed at Ollama's OpenAI-compatible endpoint.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

import openai

logger = logging.getLogger(__name__)


class OllamaClient:
    """
    Async LLM client for Ollama via OpenAI-compatible API.
    Supports JSON mode, retries, and concurrency limiting.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434/v1",
        model: str = "gemma4:e2b",
        max_concurrent: int = 8,
        timeout_s: int = 90,
        max_retries: int = 3,
    ):
        self.model = model
        self.max_concurrent = max_concurrent
        self.timeout_s = timeout_s
        self.max_retries = max_retries
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._client = openai.AsyncOpenAI(
            base_url=base_url,
            api_key="ollama",  # Ollama doesn't need a real key
            timeout=timeout_s,
        )
        self._sync_client = openai.OpenAI(
            base_url=base_url,
            api_key="ollama",
            timeout=timeout_s,
        )
        self.total_calls = 0
        self.total_errors = 0

    async def complete(
        self,
        system: str,
        user: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        """
        Generate a text completion.
        Returns the response text content.
        """
        async with self._semaphore:
            for attempt in range(self.max_retries):
                try:
                    resp = await self._client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": system},
                            {"role": "user", "content": user},
                        ],
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                    self.total_calls += 1
                    return resp.choices[0].message.content or ""
                except Exception as e:
                    self.total_errors += 1
                    wait = 2 ** attempt
                    logger.warning(
                        f"LLM call failed (attempt {attempt+1}/{self.max_retries}): {e}. "
                        f"Retrying in {wait}s..."
                    )
                    await asyncio.sleep(wait)

            logger.error("LLM call failed after all retries")
            return ""

    async def complete_json(
        self,
        system: str,
        user: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> dict | list | None:
        """
        Generate a JSON completion. Parses the response as JSON.
        Retries with a fix prompt on parse failure.
        """
        system_with_json = (
            system + "\n\nIMPORTANT: Respond with ONLY valid JSON. "
            "No markdown fences, no prose, no explanation."
        )
        text = await self.complete(system_with_json, user, temperature, max_tokens)
        parsed = self._extract_json(text)

        if parsed is not None:
            return parsed

        # Retry with fix prompt
        fix_prompt = (
            f"The following text was supposed to be valid JSON but failed to parse:\n"
            f"---\n{text[:500]}\n---\n"
            f"Please fix it and return ONLY valid JSON."
        )
        text2 = await self.complete(system_with_json, fix_prompt, 0.3, max_tokens)
        parsed2 = self._extract_json(text2)
        if parsed2 is not None:
            return parsed2

        logger.warning(f"Failed to parse JSON after retry. Raw: {text[:200]}")
        return None

    def complete_sync(
        self,
        system: str,
        user: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        """Synchronous completion for use outside async contexts."""
        for attempt in range(self.max_retries):
            try:
                resp = self._sync_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                self.total_calls += 1
                return resp.choices[0].message.content or ""
            except Exception as e:
                self.total_errors += 1
                logger.warning(f"Sync LLM call failed: {e}")
                import time
                time.sleep(2 ** attempt)
        return ""

    def is_available(self) -> bool:
        """Check if Ollama is running and the model is available."""
        try:
            resp = self._sync_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=5,
            )
            return bool(resp.choices)
        except Exception as e:
            logger.info(f"Ollama not available: {e}")
            return False

    @staticmethod
    def _extract_json(text: str) -> dict | list | None:
        """Extract JSON from text, handling markdown fences and extra text."""
        if not text:
            return None

        # Try direct parse
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try stripping markdown fences
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Try finding first { or [
        for start_char, end_char in [("{", "}"), ("[", "]")]:
            start = text.find(start_char)
            if start >= 0:
                # Find matching end
                depth = 0
                for i in range(start, len(text)):
                    if text[i] == start_char:
                        depth += 1
                    elif text[i] == end_char:
                        depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(text[start:i + 1])
                        except json.JSONDecodeError:
                            break

        return None
