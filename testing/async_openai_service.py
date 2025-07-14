"""
Async OpenAI API service with key rotation and load balancing
Similar to USDA API service but for OpenAI operations
"""

import asyncio
import aiohttp
import json
import base64
import time
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
from decouple import config
from dotenv import load_dotenv
import threading

# Load environment variables
load_dotenv()


class AsyncOpenAIService:
    """Async OpenAI API service with key rotation and concurrent request handling"""

    def __init__(self):
        # Load OpenAI API keys
        api_keys_str = config("OPENAI_API_KEYS", default="[]", cast=str)
        try:
            self.api_keys = json.loads(api_keys_str)
        except json.JSONDecodeError:
            # Fallback to single key
            single_key = config("OPENAI_API_KEY", default=None)
            if single_key:
                self.api_keys = [single_key]
            else:
                raise ValueError("No OpenAI API keys found in environment variables")

        if not self.api_keys:
            raise ValueError("No OpenAI API keys found")

        # Initialize key rotation
        self.key_usage_count = {i: 0 for i in range(len(self.api_keys))}
        self.key_last_used = {i: 0 for i in range(len(self.api_keys))}
        self.key_lock = threading.Lock()

        # API configuration
        self.base_url = "https://api.openai.com/v1"
        self.max_retries = 3
        self.retry_delay = 1

        # Rate limiting
        self.requests_per_minute = 50  # Conservative limit
        self.request_timestamps = {i: [] for i in range(len(self.api_keys))}

        print(f"🔑 Initialized AsyncOpenAIService with {len(self.api_keys)} API key(s)")

    def _get_best_key_index(self) -> int:
        """Get the best API key index based on usage and rate limits"""
        with self.key_lock:
            current_time = time.time()
            best_index = 0
            min_recent_requests = float("inf")

            for i in range(len(self.api_keys)):
                # Remove old timestamps (older than 1 minute)
                self.request_timestamps[i] = [
                    ts for ts in self.request_timestamps[i] if current_time - ts < 60
                ]

                recent_requests = len(self.request_timestamps[i])

                # Find key with least recent requests
                if recent_requests < min_recent_requests:
                    min_recent_requests = recent_requests
                    best_index = i

            # Record usage
            self.request_timestamps[best_index].append(current_time)
            self.key_usage_count[best_index] += 1
            self.key_last_used[best_index] = current_time

            return best_index

    def _get_headers(self, key_index: int) -> Dict[str, str]:
        """Get headers for API request"""
        return {
            "Authorization": f"Bearer {self.api_keys[key_index]}",
            "Content-Type": "application/json",
        }

    async def _make_request(
        self,
        session: aiohttp.ClientSession,
        method: str,
        endpoint: str,
        data: Dict[str, Any],
        timeout: int = 60,
    ) -> Optional[Dict[str, Any]]:
        """Make async request with retry logic and key rotation"""

        for attempt in range(self.max_retries):
            key_index = self._get_best_key_index()
            headers = self._get_headers(key_index)
            url = f"{self.base_url}/{endpoint}"

            try:
                async with session.request(
                    method,
                    url,
                    json=data,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                ) as response:

                    if response.status == 200:
                        return await response.json()
                    elif response.status == 429:
                        print(
                            f"⚠️  Rate limit on key {key_index + 1}, attempt {attempt + 1}"
                        )
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                    elif response.status == 401:
                        print(f"❌ Invalid API key {key_index + 1}")
                        await asyncio.sleep(self.retry_delay)
                    else:
                        error_text = await response.text()
                        print(f"❌ API error {response.status}: {error_text}")
                        await asyncio.sleep(self.retry_delay)

            except asyncio.TimeoutError:
                print(f"⏰ Request timeout on attempt {attempt + 1}")
                await asyncio.sleep(self.retry_delay)
            except Exception as e:
                print(f"❌ Request error on attempt {attempt + 1}: {e}")
                await asyncio.sleep(self.retry_delay)

        return None

    async def analyze_image(
        self,
        image_path: str,
        prompt: str = None,
        model: str = "gpt-4o",
        max_tokens: int = 1000,
    ) -> Optional[Dict[str, Any]]:
        """Analyze image using OpenAI Vision API"""

        # Load default prompt if not provided
        if not prompt:
            prompt_file = Path(__file__).parent / "food_prompt.txt"
            if prompt_file.exists():
                with open(prompt_file, "r", encoding="utf-8") as f:
                    prompt = f.read()
            else:
                prompt = "Analyze this image and describe what you see."

        # Encode image
        try:
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode("utf-8")
        except Exception as e:
            print(f"❌ Error encoding image: {e}")
            return None

        # Prepare request data
        data = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            },
                        },
                    ],
                }
            ],
            "max_tokens": max_tokens,
            "temperature": 0.1,
        }

        async with aiohttp.ClientSession() as session:
            result = await self._make_request(session, "POST", "chat/completions", data)

            if result:
                # Try to extract JSON from response
                try:
                    content = result["choices"][0]["message"]["content"]
                    # Try to find JSON in response
                    import re

                    json_match = re.search(r"\{.*\}", content, re.DOTALL)
                    if json_match:
                        return {
                            "success": True,
                            "data": json.loads(json_match.group()),
                            "raw_response": content,
                        }
                    else:
                        return {
                            "success": True,
                            "data": {"text": content},
                            "raw_response": content,
                        }
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Failed to parse response: {e}",
                        "raw_response": result,
                    }

            return {"success": False, "error": "API request failed"}

    async def process_text(
        self,
        prompt: str,
        model: str = "gpt-4o-mini",
        max_tokens: int = 500,
        temperature: float = 0.1,
    ) -> Optional[Dict[str, Any]]:
        """Process text using OpenAI API"""

        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        async with aiohttp.ClientSession() as session:
            result = await self._make_request(session, "POST", "chat/completions", data)

            if result:
                return {
                    "success": True,
                    "data": result["choices"][0]["message"]["content"],
                    "usage": result.get("usage", {}),
                }

            return {"success": False, "error": "API request failed"}

    async def batch_analyze_images(
        self,
        image_paths: List[str],
        prompts: Optional[List[str]] = None,
        model: str = "gpt-4o",
        max_tokens: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Analyze multiple images concurrently"""

        if prompts is None:
            prompts = [None] * len(image_paths)
        elif len(prompts) != len(image_paths):
            raise ValueError("Number of prompts must match number of images")

        # Create tasks for concurrent execution
        tasks = []
        for image_path, prompt in zip(image_paths, prompts):
            task = self.analyze_image(image_path, prompt, model, max_tokens)
            tasks.append(task)

        # Execute all tasks concurrently
        print(f"🚀 Processing {len(tasks)} images concurrently...")
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    {
                        "success": False,
                        "error": str(result),
                        "image_path": image_paths[i],
                    }
                )
            else:
                if result:
                    result["image_path"] = image_paths[i]
                processed_results.append(result)

        return processed_results

    async def batch_process_texts(
        self,
        prompts: List[str],
        model: str = "gpt-4o-mini",
        max_tokens: int = 500,
        temperature: float = 0.1,
    ) -> List[Dict[str, Any]]:
        """Process multiple text prompts concurrently"""

        # Create tasks for concurrent execution
        tasks = []
        for prompt in prompts:
            task = self.process_text(prompt, model, max_tokens, temperature)
            tasks.append(task)

        # Execute all tasks concurrently
        print(f"🚀 Processing {len(tasks)} text prompts concurrently...")
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    {"success": False, "error": str(result), "prompt": prompts[i]}
                )
            else:
                if result:
                    result["prompt"] = prompts[i]
                processed_results.append(result)

        return processed_results

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get API usage statistics"""
        return {
            "total_keys": len(self.api_keys),
            "key_usage_count": self.key_usage_count.copy(),
            "key_last_used": {
                k: time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(v))
                for k, v in self.key_last_used.items()
            },
            "current_rate_limits": {
                k: len(timestamps) for k, timestamps in self.request_timestamps.items()
            },
        }


# Utility functions for easy testing
async def test_single_image(service: AsyncOpenAIService, image_path: str):
    """Test single image analysis"""
    print(f"📸 Analyzing single image: {Path(image_path).name}")

    start_time = time.time()
    result = await service.analyze_image(image_path)
    end_time = time.time()

    print(f"⏱️  Processing time: {end_time - start_time:.2f} seconds")

    if result and result.get("success"):
        print("✅ Analysis successful!")
        print(json.dumps(result.get("data", {}), indent=2, ensure_ascii=False))
    else:
        print("❌ Analysis failed!")
        print(result)


async def test_batch_images(service: AsyncOpenAIService, image_paths: List[str]):
    """Test batch image analysis"""
    print(f"📸 Analyzing {len(image_paths)} images concurrently...")

    start_time = time.time()
    results = await service.batch_analyze_images(image_paths)
    end_time = time.time()

    print(f"⏱️  Total processing time: {end_time - start_time:.2f} seconds")
    print(
        f"⚡ Average time per image: {(end_time - start_time) / len(image_paths):.2f} seconds"
    )

    successful = sum(1 for r in results if r and r.get("success"))
    print(f"✅ Successful analyses: {successful}/{len(results)}")

    for i, result in enumerate(results):
        print(f"\n📷 Image {i+1}: {Path(image_paths[i]).name}")
        if result and result.get("success"):
            print("✅ Success")
            if "data" in result:
                print(
                    json.dumps(result["data"], indent=2, ensure_ascii=False)[:200]
                    + "..."
                )
        else:
            print("❌ Failed")
            print(result.get("error", "Unknown error"))


async def test_batch_texts(service: AsyncOpenAIService, prompts: List[str]):
    """Test batch text processing"""
    print(f"📝 Processing {len(prompts)} text prompts concurrently...")

    start_time = time.time()
    results = await service.batch_process_texts(prompts)
    end_time = time.time()

    print(f"⏱️  Total processing time: {end_time - start_time:.2f} seconds")
    print(
        f"⚡ Average time per prompt: {(end_time - start_time) / len(prompts):.2f} seconds"
    )

    successful = sum(1 for r in results if r and r.get("success"))
    print(f"✅ Successful processes: {successful}/{len(results)}")

    for i, result in enumerate(results):
        print(f"\n📝 Prompt {i+1}: {prompts[i][:50]}...")
        if result and result.get("success"):
            print("✅ Success")
            print(f"Response: {result.get('data', '')[:100]}...")
        else:
            print("❌ Failed")
            print(result.get("error", "Unknown error"))


async def main():
    """Main test function"""
    print("🤖 Async OpenAI API Service Test")
    print("=" * 50)

    try:
        # Initialize service
        service = AsyncOpenAIService()

        # Test images directory
        test_image_dir = Path(__file__).parent / "test_images"
        if test_image_dir.exists():
            image_files = (
                list(test_image_dir.glob("*.jpg"))
                + list(test_image_dir.glob("*.jpeg"))
                + list(test_image_dir.glob("*.png"))
            )

            if image_files:
                # Test single image
                await test_single_image(service, str(image_files[0]))

                # Test batch processing if multiple images
                if len(image_files) > 1:
                    print("\n" + "=" * 50)
                    await test_batch_images(
                        service, [str(p) for p in image_files[:3]]
                    )  # Limit to 3 for testing

        # Test batch text processing
        test_prompts = [
            "What are the health benefits of apples?",
            "How many calories are in a banana?",
            "What vitamins are found in spinach?",
            "Is salmon a good source of protein?",
            "What nutrients are in brown rice?",
        ]

        print("\n" + "=" * 50)
        await test_batch_texts(service, test_prompts)

        # Print usage stats
        print("\n📊 Usage Statistics:")
        stats = service.get_usage_stats()
        print(json.dumps(stats, indent=2))

        print("\n🎉 Testing completed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
