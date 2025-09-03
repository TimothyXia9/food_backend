"""
OpenAI prompts management for food image analysis
"""

from typing import List


class FoodAnalysisPrompts:
    """
    Centralized management of OpenAI prompts for food image analysis
    Supports both Chinese and English food recognition with USDA compatibility
    """

    @staticmethod
    def get_food_identification_prompt() -> str:
        """
        Stage 1: Food identification prompt with bilingual support
        Returns both Chinese and English names to improve USDA search accuracy
        """
        return """Please identify all food items in this image. Return results in JSON format with both Chinese and English names for better database compatibility:

{
    "foods": [
        {
            "name_chinese": "苹果",
            "name_english": "apple",
            "confidence": 0.95,
            "category": "fruit"
        },
        {
            "name_chinese": "鸡胸肉",
            "name_english": "chicken breast",
            "confidence": 0.88,
            "category": "protein"
        },
        {
            "name_chinese": "米饭",
            "name_english": "cooked white rice",
            "confidence": 0.92,
            "category": "grain"
        }
    ]
}

Requirements:
- Provide both Chinese (name_chinese) and English (name_english) names
- English names should be descriptive and suitable for USDA FoodData Central search
- Use common food names, not brand names
- Include cooking method in English name when relevant (e.g., "grilled chicken", "steamed rice")
- Confidence value between 0-1
- Category should be one of: fruit, vegetable, protein, grain, dairy, snack, beverage, other
- Return only JSON, no additional text"""

    @staticmethod
    def get_portion_estimation_prompt(food_items: List[dict]) -> str:
        """
        Stage 2: Portion estimation prompt
        Takes identified foods and estimates their portions
        """
        # Create food list string for the prompt
        food_list_chinese = "、".join(
            [food.get("name_chinese", food.get("name", "")) for food in food_items]
        )
        food_list_english = ", ".join(
            [food.get("name_english", food.get("name", "")) for food in food_items]
        )

        return f"""Based on the identified foods in the image: {food_list_chinese} ({food_list_english}), 
please estimate the portion size (in grams) for each food item. Return in JSON format:

{{
    "portions": [
        {{
            "name_chinese": "米饭",
            "name_english": "cooked white rice",
            "estimated_grams": 150,
            "cooking_method": "steamed",
            "portion_description": "约1碗米饭"
        }},
        {{
            "name_chinese": "鸡胸肉", 
            "name_english": "grilled chicken breast",
            "estimated_grams": 120,
            "cooking_method": "grilled",
            "portion_description": "约1块鸡胸肉"
        }}
    ]
}}

Requirements:
- Estimate realistic portion sizes based on visual appearance
- Include both Chinese and English names (matching Stage 1 results)
- Specify cooking method when identifiable
- Provide descriptive portion description in Chinese
- Consider common serving sizes for each food type
- Return only JSON, no additional text"""

    @staticmethod
    def get_streaming_food_identification_prompt() -> str:
        """
        Stage 1 prompt for streaming analysis - focuses on basic components
        """
        return """Please identify all food items in this image, focusing on basic ingredients and components. Return results in JSON format with both Chinese and English names:

{
    "foods": [
        {
            "name_chinese": "苹果",
            "name_english": "apple",
            "confidence": 0.95
        },
        {
            "name_chinese": "香蕉",
            "name_english": "banana",
            "confidence": 0.88
        },
        {
            "name_chinese": "面包",
            "name_english": "white bread",
            "confidence": 0.92
        }
    ]
}

Requirements:
- Focus on basic food components rather than complex dishes
- Provide both Chinese (name_chinese) and English (name_english) names
- English names should be suitable for nutrition database searches
- Use descriptive English names (e.g., "cooked white rice" instead of just "rice")
- Confidence value between 0-1
- Return only JSON, no additional text"""


def get_food_identification_prompt() -> str:
    """Convenience function for backward compatibility"""
    return FoodAnalysisPrompts.get_food_identification_prompt()


def get_portion_estimation_prompt(food_items: List[dict]) -> str:
    """Convenience function for backward compatibility"""
    return FoodAnalysisPrompts.get_portion_estimation_prompt(food_items)
