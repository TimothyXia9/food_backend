#!/usr/bin/env python3
"""
Test script to verify cooking method-aware USDA search
"""

import asyncio
from food_nutrition_pipeline import FoodNutritionPipeline

async def test_cooking_method_search():
    """Test the new cooking method aware search"""
    print("🧪 Testing Cooking Method Aware USDA Search")
    print("=" * 50)
    
    # Initialize pipeline
    pipeline = FoodNutritionPipeline()
    
    # Test cases with different cooking methods
    test_cases = [
        ("broccoli", "raw"),
        ("broccoli", "steamed"),
        ("chicken breast", "raw"),
        ("chicken breast", "grilled"),
        ("salmon", "raw"),
        ("salmon", "baked"),
        ("potato", "raw"),
        ("potato", "baked"),
    ]
    
    for food_name, cooking_method in test_cases:
        print(f"\n🔍 Testing: {food_name} ({cooking_method})")
        print("-" * 30)
        
        # Test search terms generation
        search_terms = pipeline._build_search_terms_from_recognition(food_name, cooking_method)
        print(f"Generated search terms: {search_terms}")
        
        # Test actual USDA search
        try:
            result = await pipeline._search_usda_food(food_name, cooking_method, 100, max_alternatives=2)
            
            if result:
                print(f"✅ Found {result['total_alternatives']} alternatives:")
                for i, alt in enumerate(result['alternatives'], 1):
                    print(f"  {i}. {alt['description']} (Score: {alt.get('match_score', 0):.2f})")
            else:
                print("❌ No matches found")
                
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_cooking_method_search())