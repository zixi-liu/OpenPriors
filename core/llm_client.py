"""
LLM Client Abstraction Layer

Provides a unified interface for all LLM calls in the application.
Centralizes model configuration, error handling, and response parsing.
"""

import json
import re
from typing import Optional, Dict, Any, AsyncIterator, List, Union
from dataclasses import dataclass
from enum import Enum
import logging

from litellm import acompletion

logger = logging.getLogger(__name__)


class ModelType(Enum):
    """Available model types with their identifiers."""
    GPT4O = "gpt-4o"
    GPT4O_MINI = "gpt-4o-mini"
    GPT5_1 = "gpt-5.1"  # Latest frontier model - best for critical thinking, follow-ups, adaptive reasoning
    O3_MINI = "openai/o3-mini"  # For reasoning tasks
    CLAUDE_SONNET = "claude-3-5-sonnet-20241022"
    # Gemini models - best for multimodal (vision, PDFs, documents)
    GEMINI_3_PRO = "gemini/gemini-3-pro-preview"  # Newest, best multimodal
    GEMINI_25_FLASH = "gemini/gemini-2.5-flash"   # Fast, good balance
    GEMINI_25_PRO = "gemini/gemini-2.5-pro"       # High capability


@dataclass
class LLMResponse:
    """Standardized response from LLM calls."""
    content: str
    model: str
    usage: Optional[Dict[str, int]] = None
    raw_response: Optional[Any] = None


class LLMClient:
    """
    Centralized LLM client for all AI interactions.

    Usage:
        client = LLMClient()
        response = await client.complete("What is 2+2?")
        data = await client.complete_json("Return {answer: 4}")
    """

    def __init__(
        self,
        default_model: str = ModelType.GPT4O.value,
        default_temperature: float = 0.7,
        default_max_tokens: int = 4000
    ):
        self.default_model = default_model
        self.default_temperature = default_temperature
        self.default_max_tokens = default_max_tokens

    async def complete(
        self,
        prompt: str,
        system_message: str = "",
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Basic completion - returns text response.

        Args:
            prompt: User prompt/message
            system_message: Optional system message
            model: Model to use (defaults to GPT-4o)
            temperature: Sampling temperature
            max_tokens: Max output tokens

        Returns:
            LLMResponse with content and metadata
        """
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})

        return await self._call(
            messages=messages,
            model=model or self.default_model,
            temperature=temperature if temperature is not None else self.default_temperature,
            max_tokens=max_tokens or self.default_max_tokens,
            **kwargs
        )

    async def complete_chat(
        self,
        messages: List[Dict[str, str]],
        system_message: str = "",
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Chat completion with message history.

        Args:
            messages: List of {role, content} message dicts
            system_message: Optional system message (prepended)
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Max output tokens

        Returns:
            LLMResponse with content and metadata
        """
        all_messages = []
        if system_message:
            all_messages.append({"role": "system", "content": system_message})
        all_messages.extend(messages)

        return await self._call(
            messages=all_messages,
            model=model or self.default_model,
            temperature=temperature if temperature is not None else self.default_temperature,
            max_tokens=max_tokens or self.default_max_tokens,
            **kwargs
        )

    async def complete_json(
        self,
        prompt: str,
        system_message: str = "",
        model: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Completion that expects and parses JSON response.

        Args:
            prompt: User prompt (should request JSON output)
            system_message: Optional system message
            model: Model to use

        Returns:
            Parsed JSON dict

        Raises:
            ValueError: If response cannot be parsed as JSON
        """
        response = await self.complete(
            prompt=prompt,
            system_message=system_message,
            model=model,
            **kwargs
        )

        return self._parse_json(response.content)

    async def reason(
        self,
        prompt: str,
        system_message: str = "",
        **kwargs
    ) -> LLMResponse:
        """
        Use reasoning model (o3-mini) for complex analysis tasks.

        Best for:
        - Multi-step reasoning
        - Context extraction
        - Decision making
        """
        return await self.complete(
            prompt=prompt,
            system_message=system_message,
            model=ModelType.O3_MINI.value,
            **kwargs
        )

    async def reason_json(
        self,
        prompt: str,
        system_message: str = "",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Reasoning model with JSON output parsing.
        """
        response = await self.reason(
            prompt=prompt,
            system_message=system_message,
            **kwargs
        )
        return self._parse_json(response.content)

    async def complete_multimodal(
        self,
        prompt: str,
        images: Optional[List[str]] = None,
        image_urls: Optional[List[str]] = None,
        audio_files: Optional[List[str]] = None,
        system_message: str = "",
        model: Optional[str] = None,
        response_format: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Multimodal completion with images/documents/audio.
        Uses Gemini 2.5 Flash by default for best multimodal understanding.

        Args:
            prompt: Text prompt
            images: List of base64-encoded images (with or without data: prefix)
            image_urls: List of image URLs
            audio_files: List of base64-encoded audio (format: "data:audio/wav;base64,..." or raw base64)
            system_message: Optional system message
            model: Model to use (defaults to Gemini 2.5 Flash)
            response_format: Optional response format for structured output (e.g., {"type": "json_object"})

        Returns:
            LLMResponse with content
        """
        # Build content with images/audio
        content = []

        # Add images first
        if images:
            for img_base64 in images:
                # Detect image type from base64 header or default to jpeg
                if img_base64.startswith("data:"):
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": img_base64}
                    })
                else:
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"}
                    })

        if image_urls:
            for url in image_urls:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": url}
                })

        # Add audio files using litellm's file format for Gemini
        if audio_files:
            for audio_data in audio_files:
                # Ensure proper data URL format
                if audio_data.startswith("data:audio/"):
                    file_data = audio_data
                else:
                    # Default to WAV format
                    file_data = f"data:audio/wav;base64,{audio_data}"
                content.append({
                    "type": "file",
                    "file": {"file_data": file_data}
                })

        # Add text prompt
        content.append({"type": "text", "text": prompt})

        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": content})

        # Use Gemini for multimodal by default
        use_model = model or ModelType.GEMINI_25_FLASH.value

        # Build call kwargs, excluding already-handled params
        call_kwargs = {k: v for k, v in kwargs.items() if k not in ["temperature", "max_tokens"]}

        # Add response_format if specified
        if response_format:
            call_kwargs["response_format"] = response_format

        return await self._call(
            messages=messages,
            model=use_model,
            temperature=kwargs.get("temperature", 0.3),  # Lower temp for extraction
            max_tokens=kwargs.get("max_tokens", 8000),
            **call_kwargs
        )

    async def complete_multimodal_json(
        self,
        prompt: str,
        images: Optional[List[str]] = None,
        image_urls: Optional[List[str]] = None,
        system_message: str = "",
        model: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Multimodal completion with JSON output parsing.
        """
        response = await self.complete_multimodal(
            prompt=prompt,
            images=images,
            image_urls=image_urls,
            system_message=system_message,
            model=model,
            **kwargs
        )
        return self._parse_json(response.content)

    async def stream(
        self,
        prompt: str,
        system_message: str = "",
        model: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Streaming completion - yields text chunks.

        Usage:
            async for chunk in client.stream("Tell me a story"):
                print(chunk, end="")
        """
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})

        response = await acompletion(
            model=model or self.default_model,
            messages=messages,
            stream=True,
            **kwargs
        )

        async for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def _call(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> LLMResponse:
        """Internal method to make LLM API call."""
        try:
            # O-series models (o1, o3, etc.) only support temperature=1
            # Drop temperature param for these models to avoid litellm errors
            is_o_series = 'o1' in model.lower() or 'o3' in model.lower()

            call_params = {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                **kwargs
            }

            # Only add temperature for non-O-series models
            if not is_o_series:
                call_params["temperature"] = temperature

            response = await acompletion(**call_params)

            content = response.choices[0].message.content
            usage = None
            if hasattr(response, 'usage') and response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }

            return LLMResponse(
                content=content,
                model=model,
                usage=usage,
                raw_response=response
            )

        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise

    def _parse_json(self, text: str) -> Dict[str, Any]:
        """
        Parse JSON from LLM response text.
        Handles markdown code blocks and extracts JSON objects.
        """
        # Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to extract from markdown code block
        code_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if code_block_match:
            json_content = code_block_match.group(1).strip()
            try:
                return json.loads(json_content)
            except json.JSONDecodeError as e:
                logger.warning(f"Code block JSON parse failed: {e}")
                # Try to fix common JSON issues (truncated content, etc.)
                pass

        # Try to find the outermost JSON object using bracket matching
        # This is more robust than greedy regex for nested structures
        start_idx = text.find('{')
        if start_idx != -1:
            bracket_count = 0
            end_idx = start_idx
            for i, char in enumerate(text[start_idx:], start_idx):
                if char == '{':
                    bracket_count += 1
                elif char == '}':
                    bracket_count -= 1
                    if bracket_count == 0:
                        end_idx = i + 1
                        break

            if end_idx > start_idx:
                json_str = text[start_idx:end_idx]
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError as e:
                    logger.warning(f"Bracket-matched JSON parse failed: {e}")
                    pass

        # Try greedy regex for JSON object as fallback
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # Last resort: try to find JSON array
        array_match = re.search(r'\[[\s\S]*\]', text)
        if array_match:
            try:
                return {"items": json.loads(array_match.group())}
            except json.JSONDecodeError:
                pass

        raise ValueError(f"Could not parse JSON from response: {text[:200]}...")


# Global singleton instance for convenience
llm_client = LLMClient()
