"""
Integrated Food Nutrition Pipeline
Combines OpenAI image recognition with USDA nutrition data
Process: Image -> Food Recognition -> Nutrition Lookup -> Complete Results
"""

import asyncio
import json
import re
import difflib
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import time

# Import our existing services
from async_openai_service import AsyncOpenAIService
from test_usda_nutrition import USDANutritionAPI, format_nutrition_info


class FoodNutritionPipeline:
    """Complete pipeline from image to nutrition information"""

    def __init__(self):
        print("🔧 Initializing Food Nutrition Pipeline...")

        # Initialize services
        self.openai_service = AsyncOpenAIService()
        self.usda_service = USDANutritionAPI()

        # Food name mapping cache
        self.food_name_cache = {}

        print("✅ Pipeline initialized successfully!")

    def _normalize_food_name(self, food_name: str) -> str:
        """Normalize food name for better matching while preserving important cooking methods"""
        # Convert to lowercase and remove extra spaces
        normalized = re.sub(r"\s+", " ", food_name.lower().strip())

        # Only remove less important descriptors, keep cooking methods that affect nutrition
        remove_words = [
            "organic",
            "natural",
            "sliced",
            "chopped",
            "medium",
            "large",
            "small",
            "pieces",
            "fresh",  # Often redundant in USDA data
        ]

        for word in remove_words:
            normalized = re.sub(rf"\b{word}\b", "", normalized)

        # Clean up extra spaces
        normalized = re.sub(r"\s+", " ", normalized).strip()

        return normalized

    def _build_search_terms_from_recognition(
        self, food_name: str, cooking_method: str, max_results: int = 5
    ) -> List[str]:
        """Build search terms using OpenAI extracted food name and cooking method"""

        search_terms = []

        # Normalize the food name (remove size descriptors but keep important info)
        normalized_food = self._normalize_food_name(food_name)

        # Map OpenAI cooking methods to USDA terminology
        cooking_method_map = {
            "raw": "raw",
            "cooked": "cooked",
            "fried": "fried",
            "baked": "baked",
            "grilled": "grilled",
            "steamed": "steamed",
            "boiled": "boiled",
            "roasted": "roasted",
            "sauteed": "sauteed",
            "braised": "braised",
            "broiled": "broiled",
        }

        # Clean and map cooking method
        method_lower = cooking_method.lower().strip()
        usda_method = cooking_method_map.get(method_lower, method_lower)

        # Primary search: food name + cooking method
        if usda_method and usda_method != "unknown":
            primary_search = f"{normalized_food}, {usda_method}"
            search_terms.append(primary_search)

            # Alternative format: food name + cooking method (different comma placement)
            alt_search = f"{normalized_food} {usda_method}"
            search_terms.append(alt_search)

        # Secondary search: just the food name (for broader results)
        search_terms.append(normalized_food)

        # For compound foods, try breaking them down
        if "with" in normalized_food or "and" in normalized_food:
            # Extract main food component
            main_food = normalized_food.split("with")[0].split("and")[0].strip()
            if main_food != normalized_food:
                if usda_method and usda_method != "unknown":
                    search_terms.append(f"{main_food}, {usda_method}")
                search_terms.append(main_food)

        # Try without descriptors for broader search
        words = normalized_food.split()
        if len(words) > 1:
            # Try most important words (usually the first one or two)
            main_words = words[:2] if len(words) > 2 else words
            main_food_simplified = " ".join(main_words)

            if usda_method and usda_method != "unknown":
                search_terms.append(f"{main_food_simplified}, {usda_method}")
            search_terms.append(main_food_simplified)

        # Remove duplicates while preserving order
        unique_terms = []
        for term in search_terms:
            if term and term.strip() and term not in unique_terms:
                unique_terms.append(term)

        return unique_terms[:max_results]

    async def _search_usda_food(
        self,
        food_name: str,
        cooking_method: str,
        estimated_weight: float,
        max_alternatives: int = 3,
    ) -> Optional[Dict[str, Any]]:
        """Search for food in USDA database using OpenAI extracted food name and cooking method"""

        # Create cache key that includes cooking method
        cache_key = f"{food_name.lower()}_{cooking_method.lower()}"
        if cache_key in self.food_name_cache:
            cached_result = self.food_name_cache[cache_key]
            # For cached results, we need to return the proper format
            primary_nutrition = self._calculate_nutrition_for_weight(
                cached_result, estimated_weight
            )
            return {
                "primary_match": primary_nutrition,
                "alternatives": [primary_nutrition],
                "total_alternatives": 1,
            }

        # Get search terms using OpenAI recognition data
        search_terms = self._build_search_terms_from_recognition(
            food_name, cooking_method
        )

        print(
            f"🔍 Searching USDA for '{food_name}' ({cooking_method}) using terms: {search_terms}"
        )

        # Collect all potential matches with scores
        all_matches = []

        for search_term in search_terms:
            try:
                # Search USDA database
                search_results = self.usda_service.search_foods(
                    search_term, page_size=15
                )

                if not search_results or not search_results.get("foods"):
                    continue

                # Score all matches
                for food_item in search_results["foods"]:
                    description = food_item.get("description", "").lower()

                    # Calculate similarity score
                    similarity = difflib.SequenceMatcher(
                        None,
                        self._normalize_food_name(food_name),
                        self._normalize_food_name(description),
                    ).ratio()

                    # Boost score for exact word matches
                    food_words = set(self._normalize_food_name(food_name).split())
                    desc_words = set(self._normalize_food_name(description).split())
                    word_match_bonus = len(food_words.intersection(desc_words)) * 0.1

                    # Bonus for common data types (Foundation, SR Legacy are more reliable)
                    data_type_bonus = (
                        0.05
                        if food_item.get("dataType") in ["Foundation", "SR Legacy"]
                        else 0
                    )

                    total_score = similarity + word_match_bonus + data_type_bonus

                    # Only include matches above minimum threshold
                    if total_score > 0.3:
                        all_matches.append(
                            {
                                "food_item": food_item,
                                "score": total_score,
                                "search_term": search_term,
                            }
                        )

            except Exception as e:
                print(f"❌ Error searching for '{search_term}': {e}")
                continue

        if not all_matches:
            print(f"❌ No suitable matches found for '{food_name}' in USDA database")
            return None

        # Sort by score and remove duplicates (same FDC ID)
        all_matches.sort(key=lambda x: x["score"], reverse=True)
        unique_matches = []
        seen_fdc_ids = set()

        for match in all_matches:
            fdc_id = match["food_item"].get("fdcId")
            if fdc_id and fdc_id not in seen_fdc_ids:
                unique_matches.append(match)
                seen_fdc_ids.add(fdc_id)
                if len(unique_matches) >= max_alternatives:
                    break

        print(f"✅ Found {len(unique_matches)} alternatives:")
        for i, match in enumerate(unique_matches, 1):
            print(
                f"  {i}. {match['food_item'].get('description')} (score: {match['score']:.2f})"
            )

        # Get detailed nutrition information for all alternatives
        alternatives = []

        for match in unique_matches:
            fdc_id = match["food_item"].get("fdcId")
            if not fdc_id:
                continue

            try:
                detailed_info = self.usda_service.get_food_details(fdc_id)
                nutrition_info = format_nutrition_info(detailed_info)

                if nutrition_info:
                    # Calculate nutrition for the estimated weight
                    nutrition_with_weight = self._calculate_nutrition_for_weight(
                        nutrition_info, estimated_weight
                    )

                    # Add matching metadata
                    nutrition_with_weight.update(
                        {
                            "match_score": match["score"],
                            "search_term_used": match["search_term"],
                            "data_type": match["food_item"].get("dataType", "Unknown"),
                        }
                    )

                    alternatives.append(nutrition_with_weight)

            except Exception as e:
                print(f"❌ Error getting nutrition details for FDC ID {fdc_id}: {e}")
                continue

        if not alternatives:
            return None

        # Cache the best result
        self.food_name_cache[cache_key] = alternatives[0]

        # Return all alternatives
        return {
            "primary_match": alternatives[0],
            "alternatives": alternatives,
            "total_alternatives": len(alternatives),
        }

    def _calculate_nutrition_for_weight(
        self, nutrition_info: Dict, estimated_weight_grams: float
    ) -> Dict[str, Any]:
        """Calculate nutrition values for the estimated weight (USDA data is per 100g)"""

        # Weight factor (USDA data is per 100g)
        weight_factor = estimated_weight_grams / 100.0

        # Calculate adjusted nutrition values
        adjusted_nutrients = {}
        for nutrient_name, amount in nutrition_info.get("nutrients", {}).items():
            if isinstance(amount, (int, float)):
                adjusted_nutrients[nutrient_name] = round(amount * weight_factor, 2)
            else:
                adjusted_nutrients[nutrient_name] = amount

        return {
            "description": nutrition_info.get("description", "Unknown"),
            "fdc_id": nutrition_info.get("fdc_id"),
            "estimated_weight_grams": estimated_weight_grams,
            "nutrition_per_100g": nutrition_info.get("nutrients", {}),
            "nutrition_for_portion": adjusted_nutrients,
            "data_source": "USDA FoodData Central",
        }

    async def analyze_food_image(self, image_path: str) -> Optional[Dict[str, Any]]:
        """Analyze food image and return recognized foods with nutrition info"""

        print(f"📸 Analyzing image: {Path(image_path).name}")

        # Step 1: Recognize foods in image using OpenAI
        print("🤖 Step 1: Food recognition with OpenAI...")
        recognition_result = await self.openai_service.analyze_image(image_path)

        if not recognition_result or not recognition_result.get("success"):
            print("❌ Food recognition failed")
            return None

        recognized_foods = recognition_result.get("data", {}).get("foods", [])
        if not recognized_foods:
            print("❌ No foods recognized in image")
            return None

        print(f"✅ Recognized {len(recognized_foods)} food items")

        # Step 2: Get nutrition information for each food
        print("🥗 Step 2: Looking up nutrition information...")

        results = []
        total_nutrition = {
            "Energy (kcal)": 0,
            "Protein (g)": 0,
            "Total lipid (fat) (g)": 0,
            "Carbohydrate, by difference (g)": 0,
            "Fiber, total dietary (g)": 0,
        }

        for i, food_item in enumerate(recognized_foods, 1):
            food_name = food_item.get("en_name", "")
            estimated_weight = food_item.get("estimated_weight_grams", 100)
            confidence = food_item.get("confidence", 0)
            method = food_item.get("method", "unknown")

            print(f"  📋 {i}. Processing '{food_name}' ({estimated_weight}g)...")

            # Get nutrition info from USDA (with alternatives)
            usda_results = await self._search_usda_food(
                food_name, method, estimated_weight, max_alternatives=3
            )

            food_result = {
                "recognized_name": food_name,
                "estimated_weight_grams": estimated_weight,
                "confidence": confidence,
                "cooking_method": method,
                "usda_matches": usda_results,
                "status": "success" if usda_results else "no_nutrition_data",
            }

            # Add to totals using primary match
            if usda_results and usda_results.get("primary_match", {}).get(
                "nutrition_for_portion"
            ):
                portion_nutrition = usda_results["primary_match"][
                    "nutrition_for_portion"
                ]
                for key in total_nutrition.keys():
                    if key in portion_nutrition:
                        total_nutrition[key] += portion_nutrition[key]

            results.append(food_result)

        return {
            "image_path": image_path,
            "processing_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_foods_recognized": len(recognized_foods),
            "foods_with_nutrition": sum(1 for r in results if r["status"] == "success"),
            "individual_foods": results,
            "total_nutrition_summary": total_nutrition,
            "openai_raw_response": recognition_result.get("raw_response"),
        }

    async def batch_analyze_images(
        self, image_paths: List[str]
    ) -> List[Dict[str, Any]]:
        """Analyze multiple images concurrently"""

        print(f"🚀 Batch processing {len(image_paths)} images...")

        # Create tasks for concurrent execution
        tasks = []
        for image_path in image_paths:
            task = self.analyze_food_image(image_path)
            tasks.append(task)

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    {
                        "image_path": image_paths[i],
                        "status": "error",
                        "error": str(result),
                    }
                )
            else:
                processed_results.append(result)

        return processed_results

    def print_nutrition_summary(self, result: Dict[str, Any]):
        """Print a formatted nutrition summary"""
        if not result:
            print("❌ No results to display")
            return

        print(f"\n📊 Nutrition Analysis Results")
        print("=" * 50)
        print(f"Image: {Path(result['image_path']).name}")
        print(f"Processed: {result['processing_timestamp']}")
        print(f"Foods recognized: {result['total_foods_recognized']}")
        print(f"Foods with nutrition data: {result['foods_with_nutrition']}")

        # Individual foods
        print(f"\n🍽️  Individual Foods:")
        for i, food in enumerate(result["individual_foods"], 1):
            print(f"\n{i}. {food['recognized_name']}")
            print(f"   Weight: {food['estimated_weight_grams']}g")
            print(f"   Confidence: {food['confidence']:.1%}")
            print(f"   Method: {food['cooking_method']}")

            if food["status"] == "success" and food["usda_matches"]:
                usda_data = food["usda_matches"]
                primary_match = usda_data["primary_match"]

                print(f"   🥇 Primary Match: {primary_match['description']}")
                print(
                    f"      FDC ID: {primary_match['fdc_id']} | Score: {primary_match.get('match_score', 0):.2f}"
                )

                nutrition = primary_match["nutrition_for_portion"]
                print(f"   📈 Nutrition (for {food['estimated_weight_grams']}g):")
                for nutrient, amount in nutrition.items():
                    if isinstance(amount, (int, float)) and amount > 0:
                        print(f"     • {nutrient}: {amount}")

                # Show alternatives if available
                if usda_data.get("total_alternatives", 0) > 1:
                    print(
                        f"   🔄 {usda_data['total_alternatives'] - 1} Alternative(s):"
                    )
                    for j, alt in enumerate(usda_data["alternatives"][1:], 2):
                        print(
                            f"      {j}. {alt['description']} (Score: {alt.get('match_score', 0):.2f}, FDC: {alt['fdc_id']})"
                        )
            else:
                print(f"   ❌ No nutrition data found")

        # Total summary
        print(f"\n🧮 Total Nutrition Summary:")
        total = result["total_nutrition_summary"]
        for nutrient, amount in total.items():
            if amount > 0:
                print(f"  • {nutrient}: {amount:.1f}")

    def export_alternatives_json(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Export all alternatives in a structured JSON format for frontend use"""
        if not result or not result.get("individual_foods"):
            return {}

        export_data = {
            "image_info": {
                "path": result["image_path"],
                "timestamp": result["processing_timestamp"],
                "total_foods": result["total_foods_recognized"],
            },
            "foods": [],
        }

        for food in result["individual_foods"]:
            food_data = {
                "recognized_name": food["recognized_name"],
                "estimated_weight_grams": food["estimated_weight_grams"],
                "confidence": food["confidence"],
                "cooking_method": food["cooking_method"],
                "alternatives": [],
            }

            if food["status"] == "success" and food["usda_matches"]:
                usda_data = food["usda_matches"]

                for i, alternative in enumerate(usda_data["alternatives"]):
                    alt_data = {
                        "rank": i + 1,
                        "is_primary": i == 0,
                        "description": alternative["description"],
                        "fdc_id": alternative["fdc_id"],
                        "match_score": alternative.get("match_score", 0),
                        "data_type": alternative.get("data_type", "Unknown"),
                        "nutrition_per_100g": alternative.get("nutrition_per_100g", {}),
                        "nutrition_for_portion": alternative.get(
                            "nutrition_for_portion", {}
                        ),
                        "estimated_weight_grams": alternative.get(
                            "estimated_weight_grams", 0
                        ),
                    }
                    food_data["alternatives"].append(alt_data)

            export_data["foods"].append(food_data)

        # Add total nutrition using primary matches
        export_data["total_nutrition"] = result.get("total_nutrition_summary", {})

        return export_data


# Test functions
async def test_single_image(pipeline: FoodNutritionPipeline, image_path: str):
    """Test single image processing"""
    print(f"🧪 Testing single image: {Path(image_path).name}")

    start_time = time.time()
    result = await pipeline.analyze_food_image(image_path)
    end_time = time.time()

    print(f"⏱️  Total processing time: {end_time - start_time:.2f} seconds")

    if result:
        pipeline.print_nutrition_summary(result)

        # Export alternatives in JSON format
        print(f"\n📄 JSON Export with Alternatives:")
        alternatives_json = pipeline.export_alternatives_json(result)

        # Show compact JSON for each food
        for food_data in alternatives_json.get("foods", []):
            print(
                f"\n🍯 {food_data['recognized_name']} ({food_data['estimated_weight_grams']}g):"
            )
            for i, alt in enumerate(food_data["alternatives"], 1):
                status = "🥇" if alt["is_primary"] else f"  {i}"
                print(f"  {status} {alt['description']}")
                print(
                    f"      FDC: {alt['fdc_id']} | Score: {alt['match_score']:.2f} | Type: {alt['data_type']}"
                )
    else:
        print("❌ Analysis failed")

    return result


async def test_batch_images(pipeline: FoodNutritionPipeline, image_paths: List[str]):
    """Test batch image processing"""
    print(f"🧪 Testing batch processing: {len(image_paths)} images")

    start_time = time.time()
    results = await pipeline.batch_analyze_images(image_paths)
    end_time = time.time()

    print(f"⏱️  Total batch processing time: {end_time - start_time:.2f} seconds")
    print(
        f"⚡ Average time per image: {(end_time - start_time) / len(image_paths):.2f} seconds"
    )

    # Summary statistics
    successful = sum(1 for r in results if r and "total_foods_recognized" in r)
    total_foods = sum(r.get("total_foods_recognized", 0) for r in results if r)
    foods_with_nutrition = sum(r.get("foods_with_nutrition", 0) for r in results if r)

    print(f"\n📊 Batch Results Summary:")
    print(f"  • Successful analyses: {successful}/{len(results)}")
    print(f"  • Total foods recognized: {total_foods}")
    print(f"  • Foods with nutrition data: {foods_with_nutrition}")

    return results


async def main():
    """Main test function"""
    print("🍎 Food Nutrition Pipeline Test")
    print("=" * 50)

    try:
        # Initialize pipeline
        pipeline = FoodNutritionPipeline()

        # Check for test images
        test_image_dir = Path(__file__).parent / "test_images"
        if not test_image_dir.exists():
            print("❌ No test_images directory found")
            return

        image_files = (
            list(test_image_dir.glob("*.jpg"))
            + list(test_image_dir.glob("*.jpeg"))
            + list(test_image_dir.glob("*.png"))
        )

        if not image_files:
            print("❌ No images found in test_images directory")
            return

        print(f"📸 Found {len(image_files)} test images")

        # Test single image
        if image_files:
            await test_single_image(pipeline, str(image_files[0]))

        # Test batch processing if multiple images
        if len(image_files) > 1:
            print("\n" + "=" * 50)
            await test_batch_images(
                pipeline, [str(p) for p in image_files[:2]]
            )  # Limit for testing

        print("\n🎉 All tests completed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
