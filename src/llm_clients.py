"""Thin LLM client wrappers for the three-model ensemble.

Each client exposes the same tiny interface:

    client.name                      -> "claude" | "openai" | "gemini"
    client.complete(system, user)    -> LLMResult(text, ok, error)

- SDKs are imported lazily inside each client, so importing this module (and
  running the offline tests with MockClient) needs no SDKs or API keys.
- get_default_clients() builds whichever real clients have a key present in the
  environment, so a missing key just drops that model from the ensemble.
- A model that errors returns LLMResult(ok=False); the reasoner treats that as
  an abstention (it is not counted in the confidence vote).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol


@dataclass
class LLMResult:
    text: str
    model: str
    ok: bool = True
    error: str | None = None


class LLMClient(Protocol):
    name: str

    def complete(self, system: str, user: str) -> LLMResult: ...


# --- real providers (lazy SDK imports) ---------------------------------------

class AnthropicClient:
    name = "claude"

    def __init__(self, model: str | None = None):
        self.model = model or os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

    def complete(self, system: str, user: str) -> LLMResult:
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
            resp = client.messages.create(
                model=self.model,
                max_tokens=800,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return LLMResult(text=resp.content[0].text, model=self.name)
        except Exception as e:  # network/key/parse errors -> abstain
            return LLMResult(text="", model=self.name, ok=False, error=str(e))


class OpenAIClient:
    name = "openai"

    def __init__(self, model: str | None = None):
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def complete(self, system: str, user: str) -> LLMResult:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
            resp = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            return LLMResult(text=resp.choices[0].message.content, model=self.name)
        except Exception as e:
            return LLMResult(text="", model=self.name, ok=False, error=str(e))


class GeminiClient:
    name = "gemini"

    def __init__(self, model: str | None = None):
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    def complete(self, system: str, user: str) -> LLMResult:
        try:
            import google.generativeai as genai

            genai.configure(api_key=os.environ["GEMINI_API_KEY"])
            # Gemini has no separate system role; prepend it as system_instruction.
            model = genai.GenerativeModel(self.model, system_instruction=system)
            resp = model.generate_content(user)
            return LLMResult(text=resp.text, model=self.name)
        except Exception as e:
            return LLMResult(text="", model=self.name, ok=False, error=str(e))


# --- mock (offline tests / demos without keys) -------------------------------

class MockClient:
    """Returns a canned response. Used for offline testing of the pipeline."""

    def __init__(self, name: str, response: str):
        self.name = name
        self._response = response

    def complete(self, system: str, user: str) -> LLMResult:
        return LLMResult(text=self._response, model=self.name)


# --- factory -----------------------------------------------------------------

def get_default_clients() -> list[LLMClient]:
    """Build real clients for whichever API keys are present in the environment."""
    clients: list[LLMClient] = []
    if os.getenv("ANTHROPIC_API_KEY"):
        clients.append(AnthropicClient())
    if os.getenv("OPENAI_API_KEY"):
        clients.append(OpenAIClient())
    if os.getenv("GEMINI_API_KEY"):
        clients.append(GeminiClient())
    return clients
