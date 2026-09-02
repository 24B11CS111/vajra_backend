import json
import re
from abc import ABC, abstractmethod
from typing import AsyncIterator, Callable, Dict, Any, Optional
import httpx

from app.core.config import settings


class LLMProviderError(Exception):
    """Base exception for controlled LLM provider failures."""


class LLMConfigurationError(LLMProviderError):
    """Raised when the selected provider is missing required configuration."""


class LLMResponseError(LLMProviderError):
    """Raised when a provider returns an unusable response."""


class LLMProvider(ABC):
    def validate_configuration(self) -> None:
        return None

    @abstractmethod
    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        pass

    @abstractmethod
    async def extract_json(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        pass

    async def stream_generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> AsyncIterator[str]:
        yield await self.generate(prompt, system_prompt=system_prompt)

    @abstractmethod
    def estimate_tokens(self, text: str) -> int:
        pass


class DummyProvider(LLMProvider):
    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        return "This is a simulated LLM response."

    async def extract_json(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        if "like" in prompt.lower() or "love" in prompt.lower() or "prefer" in prompt.lower():
            return {
                "memories": [
                    {
                        "content": prompt,
                        "memory_type": "preference",
                        "confidence": 0.9,
                        "importance": 0.8,
                        "tags": ["preference"]
                    }
                ]
            }
        return {"memories": []}

    def estimate_tokens(self, text: str) -> int:
        return len(text) // 4


class OpenRouterProvider(LLMProvider):
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        self.model = model or settings.OPENROUTER_MODEL
        self.base_url = (base_url or settings.OPENROUTER_BASE_URL).rstrip("/")

    def validate_configuration(self) -> None:
        if not self.api_key:
            raise LLMConfigurationError("OpenRouter provider is missing OPENROUTER_API_KEY.")

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://vajra.ai",
            "X-Title": "VAJRA Mobile Companion",
            "Content-Type": "application/json",
        }

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        self.validate_configuration()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 1024,
            "temperature": 0.7,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._get_headers(),
                    json=payload,
                )
                if response.status_code != 200:
                    raise LLMProviderError(f"OpenRouter returned status {response.status_code}: {response.text[:200]}")
                
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                if not content:
                    raise LLMResponseError("OpenRouter returned an empty message.")
                return content.strip()
        except LLMProviderError:
            raise
        except Exception as exc:
            raise LLMProviderError(f"OpenRouter generation failed: {exc}") from exc

    async def extract_json(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        json_prompt = (
            f"{prompt}\n\n"
            "CRITICAL: Return ONLY valid, raw JSON. Do not wrap in markdown codeblocks (no ```json). Do not add preamble."
        )
        raw_text = await self.generate(json_prompt, system_prompt=system_prompt)
        
        # Clean markdown code fences if present
        clean_text = raw_text.strip()
        if clean_text.startswith("```"):
            clean_text = re.sub(r"^```(?:json)?\s*", "", clean_text)
            clean_text = re.sub(r"\s*```$", "", clean_text)
        
        try:
            return json.loads(clean_text)
        except json.JSONDecodeError as exc:
            # Fallback regex extraction of first JSON object
            json_match = re.search(r"\{.*\}", clean_text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except Exception:
                    pass
            raise LLMResponseError(f"Malformed JSON from LLM: {clean_text[:100]}") from exc

    async def stream_generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> AsyncIterator[str]:
        self.validate_configuration()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 1024,
            "temperature": 0.7,
            "stream": True,
        }

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers=self._get_headers(),
                    json=payload,
                ) as response:
                    if response.status_code != 200:
                        err_text = await response.aread()
                        raise LLMProviderError(f"OpenRouter streaming status {response.status_code}: {err_text[:200]}")

                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        if line.startswith("data: "):
                            data_str = line[6:].strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                chunk_json = json.loads(data_str)
                                delta = chunk_json["choices"][0].get("delta", {}).get("content", "")
                                if delta:
                                    yield delta
                            except Exception:
                                pass
        except LLMProviderError:
            raise
        except Exception as exc:
            raise LLMProviderError(f"OpenRouter streaming error: {exc}") from exc

    def estimate_tokens(self, text: str) -> int:
        return len(text) // 4


class GeminiProvider(LLMProvider):
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        client_factory: Optional[Callable[..., Any]] = None,
    ):
        self.api_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL
        self._client_factory = client_factory
        self._client = None

    def _get_client(self):
        self.validate_configuration()

        if self._client is None:
            try:
                if self._client_factory is None:
                    from google import genai

                    self._client_factory = genai.Client
                self._client = self._client_factory(api_key=self.api_key)
            except LLMConfigurationError:
                raise
            except Exception as exc:
                raise LLMProviderError("Gemini client initialization failed.") from exc

        return self._client

    def validate_configuration(self) -> None:
        if not self.api_key:
            raise LLMConfigurationError("Gemini provider is missing GEMINI_API_KEY.")

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        try:
            client = self._get_client()
            response = await client.aio.models.generate_content(
                model=self.model,
                contents=prompt,
                config=self._generation_config(system_prompt),
            )
            return self._extract_text_response(response)
        except LLMProviderError:
            raise
        except Exception as exc:
            raise LLMProviderError("Gemini generation failed.") from exc

    async def extract_json(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        json_prompt = (
            f"{prompt}\n\n"
            "Return only valid JSON. Do not wrap it in Markdown fences."
        )
        text = await self.generate(json_prompt, system_prompt=system_prompt)
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise LLMResponseError("Gemini returned malformed JSON.") from exc

    async def stream_generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> AsyncIterator[str]:
        try:
            client = self._get_client()
            stream = await client.aio.models.generate_content_stream(
                model=self.model,
                contents=prompt,
                config=self._generation_config(system_prompt),
            )
            async for chunk in stream:
                text = getattr(chunk, "text", None)
                if text:
                    yield text
        except LLMProviderError:
            raise
        except Exception as exc:
            raise LLMProviderError("Gemini streaming failed.") from exc

    def estimate_tokens(self, text: str) -> int:
        return len(text) // 4

    @staticmethod
    def _extract_text_response(response: Any) -> str:
        text = getattr(response, "text", None)
        if not text:
            raise LLMResponseError("Gemini returned an empty response.")
        return text

    @staticmethod
    def _generation_config(system_prompt: Optional[str]):
        if not system_prompt:
            return None
        try:
            from google.genai import types

            return types.GenerateContentConfig(system_instruction=system_prompt)
        except Exception:
            return {"system_instruction": system_prompt}


class OpenAIProvider(LLMProvider):
    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        raise NotImplementedError("OpenAI API not configured.")

    async def extract_json(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        raise NotImplementedError("OpenAI API not configured.")

    def estimate_tokens(self, text: str) -> int:
        return len(text) // 4


class AnthropicProvider(LLMProvider):
    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        raise NotImplementedError("Anthropic API not configured.")

    async def extract_json(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        raise NotImplementedError("Anthropic API not configured.")

    def estimate_tokens(self, text: str) -> int:
        return len(text) // 4


class LocalProvider(LLMProvider):
    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        raise NotImplementedError("Local LLM not configured.")

    async def extract_json(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        raise NotImplementedError("Local LLM not configured.")

    def estimate_tokens(self, text: str) -> int:
        return len(text) // 4


class LLMFactory:
    @staticmethod
    def get_provider() -> LLMProvider:
        provider_name = (settings.LLM_PROVIDER or "").lower()

        if provider_name == "openrouter" or (provider_name != "dummy" and settings.OPENROUTER_API_KEY):
            return OpenRouterProvider()
        elif provider_name == "gemini" or (provider_name != "dummy" and settings.GEMINI_API_KEY):
            return GeminiProvider()
        elif provider_name == "openai":
            return OpenAIProvider()
        elif provider_name == "anthropic":
            return AnthropicProvider()
        elif provider_name == "local":
            return LocalProvider()

        if settings.OPENROUTER_API_KEY:
            return OpenRouterProvider()

        return DummyProvider()
