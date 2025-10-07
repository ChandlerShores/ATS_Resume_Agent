"""Unified LLM client supporting OpenAI and Anthropic."""

import json
import os
from enum import Enum
from typing import Any

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class LLMClient:
    """
    Unified client for LLM API calls.

    Supports both OpenAI and Anthropic with a consistent interface.
    """

    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ):
        self.provider = LLMProvider(provider or os.getenv("LLM_PROVIDER", "openai"))
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Set default model based on provider
        if model:
            self.model = model
        elif self.provider == LLMProvider.OPENAI:
            self.model = os.getenv("LLM_MODEL", "gpt-4-turbo-preview")
        else:
            self.model = os.getenv("LLM_MODEL", "claude-3-5-sonnet-20241022")

        # Initialize client
        if self.provider == LLMProvider.OPENAI:
            if OpenAI is None:
                raise ImportError("openai package not installed")
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")
            self.client = OpenAI(api_key=api_key)
        else:
            if Anthropic is None:
                raise ImportError("anthropic package not installed")
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable not set")
            self.client = Anthropic(api_key=api_key)

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """
        Get completion from LLM.

        Args:
            system_prompt: System/instruction prompt
            user_prompt: User query/request
            temperature: Sampling temperature (uses default if None)
            max_tokens: Maximum tokens (uses default if None)

        Returns:
            str: LLM response text
        """
        temp = temperature if temperature is not None else self.temperature
        tokens = max_tokens if max_tokens is not None else self.max_tokens

        if self.provider == LLMProvider.OPENAI:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temp,
                max_tokens=tokens,
            )
            return response.choices[0].message.content
        else:
            # Anthropic
            response = self.client.messages.create(
                model=self.model,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                temperature=temp,
                max_tokens=tokens,
            )
            return response.content[0].text

    def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """
        Get JSON completion from LLM.

        Args:
            system_prompt: System/instruction prompt
            user_prompt: User query/request
            temperature: Sampling temperature
            max_tokens: Maximum tokens

        Returns:
            Dict[str, Any]: Parsed JSON response
        """
        # Add JSON formatting instruction
        enhanced_system = f"{system_prompt}\n\nRespond with valid JSON only, no additional text."

        response_text = self.complete(enhanced_system, user_prompt, temperature, max_tokens)

        # Extract JSON from response (handle markdown code blocks)
        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]

        return json.loads(response_text.strip())


def get_llm_client() -> LLMClient:
    """Get a configured LLM client instance."""
    return LLMClient()
