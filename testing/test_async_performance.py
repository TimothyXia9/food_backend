"""
Performance comparison test for async vs sync OpenAI API calls
Demonstrates the benefits of concurrent processing
"""

import asyncio
import time
import json
from pathlib import Path
from async_openai_service import AsyncOpenAIService


async def test_concurrent_vs_sequential():
    """Compare concurrent vs sequential processing performance"""
    print("🏃 Performance Comparison: Concurrent vs Sequential")
    print("=" * 60)

    # Initialize service
    service = AsyncOpenAIService()

    # Test prompts for text processing
    test_prompts = [
        "What are the nutritional benefits of eating carrots?",
        "How much protein is in chicken breast?",
        "What vitamins are found in oranges?",
        "Is quinoa a complete protein?",
        "What are the health benefits of green tea?",
        "How many calories are in an avocado?",
        "What nutrients are in sweet potatoes?",
        "Is dark chocolate healthy?",
    ]

    print(f"📝 Testing with {len(test_prompts)} text prompts...")

    # Test 1: Sequential processing (simulated)
    print("\n🐌 Sequential Processing (simulated):")
    sequential_start = time.time()
    sequential_results = []

    for i, prompt in enumerate(test_prompts):
        print(f"  Processing prompt {i+1}/{len(test_prompts)}...")
        result = await service.process_text(prompt)
        sequential_results.append(result)

    sequential_end = time.time()
    sequential_time = sequential_end - sequential_start

    print(f"⏱️  Sequential time: {sequential_time:.2f} seconds")
    print(f"⚡ Average per prompt: {sequential_time / len(test_prompts):.2f} seconds")

    # Wait a bit to avoid rate limiting
    await asyncio.sleep(2)

    # Test 2: Concurrent processing
    print("\n🚀 Concurrent Processing:")
    concurrent_start = time.time()
    concurrent_results = await service.batch_process_texts(test_prompts)
    concurrent_end = time.time()
    concurrent_time = concurrent_end - concurrent_start

    print(f"⏱️  Concurrent time: {concurrent_time:.2f} seconds")
    print(f"⚡ Average per prompt: {concurrent_time / len(test_prompts):.2f} seconds")

    # Calculate improvement
    improvement = (sequential_time - concurrent_time) / sequential_time * 100
    speedup = sequential_time / concurrent_time

    print(f"\n📊 Performance Results:")
    print(f"  • Time saved: {sequential_time - concurrent_time:.2f} seconds")
    print(f"  • Improvement: {improvement:.1f}%")
    print(f"  • Speedup: {speedup:.1f}x faster")

    # Success rates
    sequential_success = sum(1 for r in sequential_results if r and r.get("success"))
    concurrent_success = sum(1 for r in concurrent_results if r and r.get("success"))

    print(
        f"  • Sequential success rate: {sequential_success}/{len(sequential_results)} ({sequential_success/len(sequential_results)*100:.1f}%)"
    )
    print(
        f"  • Concurrent success rate: {concurrent_success}/{len(concurrent_results)} ({concurrent_success/len(concurrent_results)*100:.1f}%)"
    )


async def test_image_batch_processing():
    """Test batch image processing if images are available"""
    print("\n🖼️  Image Batch Processing Test")
    print("=" * 60)

    service = AsyncOpenAIService()

    # Check for test images
    test_image_dir = Path(__file__).parent / "test_images"
    if not test_image_dir.exists():
        print("❌ No test_images directory found. Skipping image tests.")
        return

    image_files = (
        list(test_image_dir.glob("*.jpg"))
        + list(test_image_dir.glob("*.jpeg"))
        + list(test_image_dir.glob("*.png"))
    )

    if not image_files:
        print("❌ No images found in test_images directory. Skipping image tests.")
        return

    print(f"📸 Found {len(image_files)} test images")

    # Test with available images (up to 3 for demo)
    test_images = [str(p) for p in image_files[:3]]

    if len(test_images) == 1:
        print("📷 Only one image available - testing single image processing")

        start_time = time.time()
        result = await service.analyze_image(test_images[0])
        end_time = time.time()

        print(f"⏱️  Processing time: {end_time - start_time:.2f} seconds")
        if result and result.get("success"):
            print("✅ Analysis successful!")
        else:
            print("❌ Analysis failed!")

    elif len(test_images) > 1:
        print(f"📷 Testing {len(test_images)} images concurrently")

        # Sequential simulation
        print("\n🐌 Sequential Processing (simulated):")
        sequential_start = time.time()
        sequential_results = []

        for i, image_path in enumerate(test_images):
            print(f"  Processing image {i+1}/{len(test_images)}...")
            result = await service.analyze_image(image_path)
            sequential_results.append(result)

        sequential_end = time.time()
        sequential_time = sequential_end - sequential_start

        print(f"⏱️  Sequential time: {sequential_time:.2f} seconds")

        # Wait to avoid rate limiting
        await asyncio.sleep(3)

        # Concurrent processing
        print("\n🚀 Concurrent Processing:")
        concurrent_start = time.time()
        concurrent_results = await service.batch_analyze_images(test_images)
        concurrent_end = time.time()
        concurrent_time = concurrent_end - concurrent_start

        print(f"⏱️  Concurrent time: {concurrent_time:.2f} seconds")

        # Calculate improvement
        if sequential_time > 0:
            improvement = (sequential_time - concurrent_time) / sequential_time * 100
            speedup = sequential_time / concurrent_time

            print(f"\n📊 Image Processing Results:")
            print(f"  • Time saved: {sequential_time - concurrent_time:.2f} seconds")
            print(f"  • Improvement: {improvement:.1f}%")
            print(f"  • Speedup: {speedup:.1f}x faster")


async def test_load_balancing():
    """Test API key load balancing"""
    print("\n⚖️  API Key Load Balancing Test")
    print("=" * 60)

    service = AsyncOpenAIService()

    print(f"🔑 Testing with {len(service.api_keys)} API keys")

    # Make multiple requests to test key rotation
    test_prompts = [
        f"What is the nutritional value of food item {i}?"
        for i in range(len(service.api_keys) * 2)  # More requests than keys
    ]

    print(f"📝 Making {len(test_prompts)} requests to test key rotation...")

    results = await service.batch_process_texts(test_prompts)

    # Check usage statistics
    stats = service.get_usage_stats()

    print(f"📊 Load Balancing Results:")
    print(f"  • Total requests: {len(test_prompts)}")
    print(
        f"  • Successful requests: {sum(1 for r in results if r and r.get('success'))}"
    )
    print(f"  • Key usage distribution:")

    for key_idx, usage_count in stats["key_usage_count"].items():
        print(f"    - Key {int(key_idx) + 1}: {usage_count} requests")

    # Check if load is reasonably balanced
    usage_values = list(stats["key_usage_count"].values())
    min_usage = min(usage_values)
    max_usage = max(usage_values)
    balance_ratio = min_usage / max_usage if max_usage > 0 else 1

    print(f"  • Load balance ratio: {balance_ratio:.2f} (1.0 = perfect balance)")

    if balance_ratio > 0.8:
        print("  ✅ Good load balancing!")
    elif balance_ratio > 0.6:
        print("  ⚠️  Moderate load balancing")
    else:
        print("  ❌ Poor load balancing")


async def main():
    """Main performance testing function"""
    print("🏁 Async OpenAI Service Performance Tests")
    print("=" * 60)

    try:
        # Test 1: Concurrent vs Sequential text processing
        await test_concurrent_vs_sequential()

        # Test 2: Image batch processing
        await test_image_batch_processing()

        # Test 3: Load balancing
        await test_load_balancing()

        print("\n🎉 All performance tests completed!")

    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
