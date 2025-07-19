"""
OpenAI API Service
Centralized service for managing OpenAI API requests and key rotation
"""

import asyncio
import json
import base64
import time
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import aiohttp
from django.conf import settings
from decouple import config

logger = logging.getLogger(__name__)


class OpenAIService:
    """Centralized OpenAI API service with key rotation and error handling"""

    def __init__(self, api_keys: Optional[List[str]] = None):
        """
        Initialize OpenAI service

        Args:
                api_keys: List of OpenAI API keys for rotation
        """
        self.api_keys = api_keys or self._load_api_keys()
        self.current_key_index = 0
        self.base_url = "https://api.openai.com/v1"
        self.default_model = "gpt-4o"
        self.default_timeout = 60

        if not self.api_keys:
            raise ValueError("No OpenAI API keys configured")

        logger.info(f"OpenAI service initialized with {len(self.api_keys)} API key(s)")

    def _load_api_keys(self) -> List[str]:
        """Load API keys from environment variables"""
        # Try to load multiple keys first
        api_keys_str = config("OPENAI_API_KEYS", default="[]", cast=str)
        try:
            if api_keys_str and isinstance(api_keys_str, str):
                api_keys = json.loads(api_keys_str)
                if api_keys and isinstance(api_keys, list):
                    return [str(key) for key in api_keys if isinstance(key, str)]
        except json.JSONDecodeError:
            pass

        # Fall back to single key
        single_key = config("OPENAI_API_KEY", default=None)
        if single_key and isinstance(single_key, str):
            return [single_key]

        return []

    def _get_current_api_key(self) -> str:
        """Get current API key"""
        return self.api_keys[self.current_key_index]

    def _rotate_api_key(self):
        """Rotate to next API key"""
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        logger.info(
            f"Rotated to API key {self.current_key_index + 1}/{len(self.api_keys)}"
        )

    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for OpenAI API"""
        return {
            "Authorization": f"Bearer {self._get_current_api_key()}",
            "Content-Type": "application/json",
        }

    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        model: str = "gpt-4o",
        temperature: float = 0.1,
        max_tokens: int = 1000,
        functions: List[Dict[str, Any]] = [],
        function_call: str = "auto",
        max_retries: int = 3,
        timeout: int = 60,
    ) -> Dict[str, Any]:
        """
        Make a chat completion request to OpenAI API

        Args:
                messages: List of messages for the conversation
                model: Model to use (default: gpt-4o)
                temperature: Sampling temperature
                max_tokens: Maximum tokens to generate
                functions: Function definitions for function calling
                function_call: Function call behavior
                max_retries: Maximum number of retries
                timeout: Request timeout in seconds

        Returns:
                API response dictionary
        """
        model = model or self.default_model
        timeout = timeout or self.default_timeout

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if functions:
            payload["functions"] = functions
            payload["function_call"] = function_call

        async with aiohttp.ClientSession() as session:
            for attempt in range(max_retries):
                try:
                    headers = self._get_headers()

                    async with session.post(
                        f"{self.base_url}/chat/completions",
                        json=payload,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=timeout),
                    ) as response:

                        if response.status == 429:
                            logger.warning(
                                f"Rate limit hit, rotating API key (attempt {attempt + 1})"
                            )
                            self._rotate_api_key()
                            continue

                        if response.status == 401:
                            logger.error("Invalid API key, rotating to next key")
                            self._rotate_api_key()
                            continue

                        response.raise_for_status()
                        result = await response.json()

                        logger.debug(
                            f"OpenAI API call successful (attempt {attempt + 1})"
                        )
                        return {
                            "success": True,
                            "data": result,
                            "usage": result.get("usage", {}),
                            "model": model,
                        }

                except asyncio.TimeoutError:
                    logger.warning(f"Request timeout (attempt {attempt + 1})")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2**attempt)  # Exponential backoff
                        continue

                except aiohttp.ClientError as e:
                    logger.error(f"HTTP error: {e} (attempt {attempt + 1})")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2**attempt)
                        continue

                except Exception as e:
                    logger.error(f"Unexpected error: {e} (attempt {attempt + 1})")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2**attempt)
                        continue

        return {
            "success": False,
            "error": "Maximum retries exceeded",
            "attempts": max_retries,
        }

    async def vision_completion(
        self,
        image_path: str,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 1000,
        max_retries: int = 3,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Make a vision completion request with image

        Args:
                image_path: Path to the image file
                prompt: Text prompt for the image
                model: Model to use (default: gpt-4o)
                temperature: Sampling temperature
                max_tokens: Maximum tokens to generate
                max_retries: Maximum number of retries
                timeout: Request timeout in seconds

        Returns:
                API response dictionary
        """
        model = model or self.default_model

        # Encode image to base64
        try:
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode("utf-8")
        except Exception as e:
            return {"success": False, "error": f"Failed to encode image: {e}"}

        # Create messages with image
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                    },
                ],
            }
        ]

        return await self.chat_completion(
            messages=messages,
            model=model or self.default_model,
            temperature=temperature,
            max_tokens=max_tokens,
            max_retries=max_retries,
            timeout=timeout or self.default_timeout,
        )

    async def function_calling_completion(
        self,
        messages: List[Dict[str, Any]],
        functions: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.0,
        max_iterations: int = 5,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Make a function calling completion with conversation management

        Args:
                messages: Initial conversation messages
                functions: Function definitions
                model: Model to use
                temperature: Sampling temperature
                max_iterations: Maximum function call iterations
                timeout: Request timeout in seconds

        Returns:
                Complete conversation result
        """
        conversation_history = messages.copy()
        function_calls = []

        for iteration in range(max_iterations):
            result = await self.chat_completion(
                messages=conversation_history,
                functions=functions,
                function_call="auto",
                model=model or self.default_model,
                temperature=temperature,
                timeout=timeout or self.default_timeout,
            )

            if not result["success"]:
                return result

            message = result["data"]["choices"][0]["message"]
            conversation_history.append(message)

            # Check if function was called
            if message.get("function_call"):
                function_call = message["function_call"]
                function_calls.append(
                    {
                        "name": function_call["name"],
                        "arguments": function_call["arguments"],
                        "iteration": iteration + 1,
                    }
                )

                # This is where external function execution would happen
                # For now, we'll return the conversation state
                return {
                    "success": True,
                    "data": result["data"],
                    "conversation_history": conversation_history,
                    "function_calls": function_calls,
                    "needs_function_execution": True,
                    "current_function_call": function_call,
                }
            else:
                # No function call, conversation is complete
                return {
                    "success": True,
                    "data": result["data"],
                    "conversation_history": conversation_history,
                    "function_calls": function_calls,
                    "needs_function_execution": False,
                    "final_response": message["content"],
                }

        return {
            "success": False,
            "error": "Maximum function calling iterations exceeded",
            "conversation_history": conversation_history,
            "function_calls": function_calls,
        }

    async def continue_function_conversation(
        self,
        conversation_history: List[Dict[str, Any]],
        function_name: str,
        function_result: Dict[str, Any],
        functions: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.0,
        max_iterations: int = 5,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Continue a function calling conversation after function execution

        Args:
                conversation_history: Previous conversation history
                function_name: Name of the executed function
                function_result: Result of the function execution
                functions: Function definitions
                model: Model to use
                temperature: Sampling temperature
                max_iterations: Maximum additional iterations
                timeout: Request timeout in seconds

        Returns:
                Continued conversation result
        """
        # Add function result to conversation
        conversation_history.append(
            {
                "role": "function",
                "name": function_name,
                "content": json.dumps(function_result),
            }
        )

        # Continue the conversation
        return await self.function_calling_completion(
            messages=conversation_history,
            functions=functions,
            model=model,
            temperature=temperature,
            max_iterations=max_iterations,
            timeout=timeout,
        )

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
        return {
            "total_keys": len(self.api_keys),
            "current_key_index": self.current_key_index,
            "base_url": self.base_url,
            "default_model": self.default_model,
        }


# Global OpenAI service instance
_openai_service = None


def get_openai_service() -> OpenAIService:
    """Get the global OpenAI service instance"""
    global _openai_service
    if _openai_service is None:
        _openai_service = OpenAIService()
    return _openai_service


# Convenience functions
async def openai_chat_completion(**kwargs) -> Dict[str, Any]:
    """Convenience function for chat completion"""
    service = get_openai_service()
    return await service.chat_completion(**kwargs)


async def openai_vision_completion(**kwargs) -> Dict[str, Any]:
    """Convenience function for vision completion"""
    service = get_openai_service()
    return await service.vision_completion(**kwargs)


async def openai_function_calling(**kwargs) -> Dict[str, Any]:
    """Convenience function for function calling"""
    service = get_openai_service()
    return await service.function_calling_completion(**kwargs)
