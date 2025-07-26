"""
Django management command to test the OpenAI service
"""

import asyncio
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings
from calorie_tracker.openai_service import get_openai_service
from calorie_tracker.two_stage_analyzer import (
    TwoStageFoodAnalyzer,
    test_two_stage_analysis,
)


class Command(BaseCommand):
    help = "Test the OpenAI service and two-stage food analyzer"

    def add_arguments(self, parser):
        parser.add_argument("--image", type=str, help="Path to image file to analyze")
        parser.add_argument(
            "--test-chat", action="store_true", help="Test basic chat completion"
        )
        parser.add_argument(
            "--test-vision", action="store_true", help="Test vision completion"
        )
        parser.add_argument(
            "--test-analyzer", action="store_true", help="Test two-stage food analyzer"
        )
        parser.add_argument("--config", type=str, help="Path to config file")

    def handle(self, *args, **options):
        """Handle the command"""

        self.stdout.write(self.style.SUCCESS("🤖 Testing OpenAI Service"))
        self.stdout.write("=" * 50)

        # Test basic service initialization
        try:
            service = get_openai_service()
            stats = service.get_usage_stats()
            self.stdout.write(f"✅ OpenAI service initialized successfully")
            self.stdout.write(f"   • Total API keys: {stats['total_keys']}")
            self.stdout.write(f"   • Current key index: {stats['current_key_index']}")
            self.stdout.write(f"   • Default model: {stats['default_model']}")
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Failed to initialize OpenAI service: {e}")
            )
            return

        # Test basic chat completion
        if options["test_chat"]:
            self.stdout.write("\n🔵 Testing Chat Completion...")
            asyncio.run(self._test_chat_completion())

        # Test vision completion
        if options["test_vision"] and options["image"]:
            self.stdout.write("\n🔵 Testing Vision Completion...")
            asyncio.run(self._test_vision_completion(options["image"]))

        # Test two-stage analyzer
        if options["test_analyzer"] and options["image"]:
            self.stdout.write("\n🔵 Testing Two-Stage Food Analyzer...")
            asyncio.run(
                self._test_two_stage_analyzer(options["image"], options.get("config"))
            )

        # Auto-test if image is provided
        if options["image"] and not any(
            [options["test_chat"], options["test_vision"], options["test_analyzer"]]
        ):
            self.stdout.write("\n🔵 Running full test suite...")
            asyncio.run(self._test_full_suite(options["image"], options.get("config")))

        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS("✅ Testing completed"))

    async def _test_chat_completion(self):
        """Test basic chat completion"""
        try:
            service = get_openai_service()

            messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "What is 2+2?"},
            ]

            result = await service.chat_completion(messages=messages, max_tokens=50)

            if result["success"]:
                response = result["data"]["choices"][0]["message"]["content"]
                self.stdout.write(f"✅ Chat completion successful")
                self.stdout.write(f"   Response: {response.strip()}")
                self.stdout.write(f"   Usage: {result['usage']}")
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f"❌ Chat completion failed: {result.get('error')}"
                    )
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Chat completion error: {e}"))

    async def _test_vision_completion(self, image_path):
        """Test vision completion"""
        try:
            service = get_openai_service()

            result = await service.vision_completion(
                image_path=image_path,
                prompt="What do you see in this image? Be brief.",
                max_tokens=100,
            )

            if result["success"]:
                response = result["data"]["choices"][0]["message"]["content"]
                self.stdout.write(f"✅ Vision completion successful")
                self.stdout.write(f"   Response: {response.strip()}")
                self.stdout.write(f"   Usage: {result['usage']}")
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f"❌ Vision completion failed: {result.get('error')}"
                    )
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Vision completion error: {e}"))

    async def _test_two_stage_analyzer(self, image_path, config_path=None):
        """Test two-stage food analyzer"""
        try:
            # Check if image exists
            if not Path(image_path).exists():
                self.stdout.write(self.style.ERROR(f"❌ Image not found: {image_path}"))
                return

            # Run the test
            result = await test_two_stage_analysis(image_path, config_path)

            if result and result.get("success"):
                self.stdout.write(f"✅ Two-stage analyzer completed successfully")
                summary = result["summary"]
                self.stdout.write(
                    f"   • Foods identified: {summary['total_foods_identified']}"
                )
                self.stdout.write(
                    f"   • Successful lookups: {summary['successful_nutrition_lookups']}"
                )
                self.stdout.write(f"   • Success rate: {summary['success_rate']}")
                self.stdout.write(
                    f"   • Total calories: {summary['total_nutrition']['calories']}"
                )
            else:
                self.stdout.write(self.style.ERROR(f"❌ Two-stage analyzer failed"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Two-stage analyzer error: {e}"))

    async def _test_full_suite(self, image_path, config_path=None):
        """Run full test suite"""
        await self._test_chat_completion()
        await self._test_vision_completion(image_path)
        await self._test_two_stage_analyzer(image_path, config_path)

    def _find_test_images(self):
        """Find test images in the testing directory"""
        test_image_dir = (
            Path(__file__).parent.parent.parent.parent / "testing" / "test_images"
        )
        if not test_image_dir.exists():
            return []

        image_files = (
            list(test_image_dir.glob("*.jpg"))
            + list(test_image_dir.glob("*.jpeg"))
            + list(test_image_dir.glob("*.png"))
        )

        return image_files
