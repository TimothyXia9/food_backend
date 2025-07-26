"""
USDA FoodData Central API integration service
"""

import json
import requests
import time
from django.conf import settings
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class USDANutritionService:
    """USDA FoodData Central API client with key rotation"""

    def __init__(self):
        # Load API keys from environment
        self.api_keys = self._load_api_keys()
        self.current_key_index = 0
        self.base_url = "https://api.nal.usda.gov/fdc/v1"

    def _load_api_keys(self) -> List[str]:
        """Load USDA API keys from settings"""
        # Try multiple ways to get API keys
        api_keys = []

        # Method 1: Single API key
        single_key = getattr(settings, "USDA_API_KEY", None)
        if single_key:
            api_keys.append(single_key)

        # Method 2: Multiple API keys (JSON array)
        keys_json = getattr(settings, "USDA_API_KEYS", "[]")
        try:
            if isinstance(keys_json, str):
                multiple_keys = json.loads(keys_json)
                api_keys.extend(multiple_keys)
            elif isinstance(keys_json, list):
                api_keys.extend(keys_json)
        except (json.JSONDecodeError, TypeError):
            pass

        # Remove duplicates while preserving order
        seen = set()
        unique_keys = []
        for key in api_keys:
            if key and key not in seen:
                seen.add(key)
                unique_keys.append(key)

        return unique_keys

    def is_available(self) -> bool:
        """Check if USDA service is available"""
        return len(self.api_keys) > 0

    def get_current_api_key(self) -> Optional[str]:
        """Get current API key"""
        if not self.api_keys:
            return None
        return self.api_keys[self.current_key_index]

    def rotate_api_key(self):
        """Rotate to next API key"""
        if len(self.api_keys) <= 1:
            return
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        logger.info(
            f"Rotated to API key {self.current_key_index + 1}/{len(self.api_keys)}"
        )

    def search_foods(
        self, query: str, page_size: int = 25, page_number: int = 1
    ) -> Dict:
        """
        Search for foods in USDA database

        Args:
                query (str): Search query
                page_size (int): Number of results per page (max 200)
                page_number (int): Page number (starts from 1)

        Returns:
                dict: Search results from USDA API
        """
        if not self.is_available():
            return {"success": False, "error": "USDA API keys not configured"}

        url = f"{self.base_url}/foods/search"
        params = {
            "api_key": self.get_current_api_key(),
            "query": query,
            "pageSize": min(page_size, 200),  # USDA API limit
            "pageNumber": page_number,
            # Don't restrict data types - let USDA return all types
            "sortBy": "dataType.keyword",
            "sortOrder": "asc",
        }

        try:
            response = requests.get(url, params=params, timeout=30)

            # Handle rate limiting
            if response.status_code == 429:
                logger.warning("USDA API rate limit reached, rotating key...")
                self.rotate_api_key()
                if self.get_current_api_key():
                    params["api_key"] = self.get_current_api_key()
                    time.sleep(1)  # Brief delay before retry
                    response = requests.get(url, params=params, timeout=30)

            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "data": data,
                    "foods": data.get("foods", []),
                    "total_hits": data.get("totalHits", 0),
                    "current_page": data.get("currentPage", page_number),
                    "total_pages": data.get("totalPages", 1),
                }
            else:
                logger.error(
                    f"USDA API error: {response.status_code} - {response.text}"
                )
                return {
                    "success": False,
                    "error": f"USDA API returned status {response.status_code}",
                }

        except requests.exceptions.RequestException as e:
            logger.error(f"USDA API request failed: {e}")
            return {"success": False, "error": f"Network error: {str(e)}"}

    def get_food_details(
        self, fdc_id: int, nutrients: Optional[List[int]] = None
    ) -> Dict:
        """
        Get detailed nutrition information for a specific food

        Args:
                fdc_id (int): Food Data Central ID
                nutrients (list): List of nutrient IDs to retrieve (optional)

        Returns:
                dict: Detailed food information
        """
        if not self.is_available():
            return {"success": False, "error": "USDA API keys not configured"}

        url = f"{self.base_url}/food/{fdc_id}"
        params = {"api_key": self.get_current_api_key()}

        if nutrients:
            params["nutrients"] = nutrients

        try:
            response = requests.get(url, params=params, timeout=30)

            # Handle rate limiting
            if response.status_code == 429:
                logger.warning("USDA API rate limit reached, rotating key...")
                self.rotate_api_key()
                if self.get_current_api_key():
                    params["api_key"] = self.get_current_api_key()
                    time.sleep(1)  # Brief delay before retry
                    response = requests.get(url, params=params, timeout=30)

            if response.status_code == 200:
                data = response.json()
                nutrition_data = self._format_nutrition_info(data)
                return {"success": True, "data": data, "nutrition_data": nutrition_data}
            else:
                logger.error(
                    f"USDA API error: {response.status_code} - {response.text}"
                )
                return {
                    "success": False,
                    "error": f"USDA API returned status {response.status_code}",
                }

        except requests.exceptions.RequestException as e:
            logger.error(f"USDA API request failed: {e}")
            return {"success": False, "error": f"Network error: {str(e)}"}

    def _format_nutrition_info(self, food_data: Dict) -> Dict:
        """Format nutrition information for consistent API response"""
        if not food_data:
            return {}

        # Extract basic information
        info = {
            "description": food_data.get("description", "N/A"),
            "fdc_id": food_data.get("fdcId", "N/A"),
            "data_type": food_data.get("dataType", "N/A"),
            "publication_date": food_data.get("publicationDate", "N/A"),
            "brand_owner": food_data.get("brandOwner", ""),
            "ingredients": food_data.get("ingredients", ""),
            "nutrients": {},
        }

        # Key nutrients we care about (per 100g)
        key_nutrients = {
            1008: {"name": "calories", "unit": "kcal"},
            1003: {"name": "protein", "unit": "g"},
            1004: {"name": "fat", "unit": "g"},
            1005: {"name": "carbs", "unit": "g"},
            1079: {"name": "fiber", "unit": "g"},
            2000: {"name": "sugar", "unit": "g"},
            1093: {"name": "sodium", "unit": "mg"},
            1087: {"name": "calcium", "unit": "mg"},
            1089: {"name": "iron", "unit": "mg"},
            1092: {"name": "potassium", "unit": "mg"},
            1104: {"name": "vitamin_a", "unit": "IU"},
            1162: {"name": "vitamin_c", "unit": "mg"},
        }

        # Extract nutrition data
        food_nutrients = food_data.get("foodNutrients", [])
        for nutrient in food_nutrients:
            nutrient_id = nutrient.get("nutrient", {}).get("id")
            if nutrient_id in key_nutrients:
                nutrient_info = key_nutrients[nutrient_id]
                amount = nutrient.get("amount", 0)
                info["nutrients"][nutrient_info["name"]] = {
                    "amount": amount,
                    "unit": nutrient_info["unit"],
                }

        # Also add flat structure for easier access in views
        nutrients = info["nutrients"]
        info["calories_per_100g"] = nutrients.get("calories", {}).get("amount", 0)
        info["protein_per_100g"] = nutrients.get("protein", {}).get("amount", 0)
        info["fat_per_100g"] = nutrients.get("fat", {}).get("amount", 0)
        info["carbs_per_100g"] = nutrients.get("carbs", {}).get("amount", 0)
        info["fiber_per_100g"] = nutrients.get("fiber", {}).get("amount", 0)
        info["sugar_per_100g"] = nutrients.get("sugar", {}).get("amount", 0)
        info["sodium_per_100g"] = nutrients.get("sodium", {}).get("amount", 0)

        return info

    def _extract_nutrition_from_search_result(self, food_item: Dict) -> Dict:
        """Extract nutrition data from search result food item"""
        nutrition = {
            "calories_per_100g": 0,
            "protein_per_100g": 0,
            "fat_per_100g": 0,
            "carbs_per_100g": 0,
            "fiber_per_100g": 0,
            "sugar_per_100g": 0,
            "sodium_per_100g": 0,
        }

        # Map nutrient IDs to our keys
        nutrient_mapping = {
            1008: "calories_per_100g",  # Energy
            1003: "protein_per_100g",  # Protein
            1004: "fat_per_100g",  # Total lipid (fat)
            1005: "carbs_per_100g",  # Carbohydrate, by difference
            1079: "fiber_per_100g",  # Fiber, total dietary
            2000: "sugar_per_100g",  # Sugars, total including NLEA
            1093: "sodium_per_100g",  # Sodium, Na
        }

        # Extract from foodNutrients if available
        food_nutrients = food_item.get("foodNutrients", [])
        has_nutrition_data = False

        for nutrient in food_nutrients:
            nutrient_id = nutrient.get("nutrientId")
            if nutrient_id in nutrient_mapping:
                key = nutrient_mapping[nutrient_id]
                value = nutrient.get("value", 0)
                if value is not None and value > 0:
                    nutrition[key] = value
                    has_nutrition_data = True

        # If no nutrition data found in search result, log it for debugging
        if not has_nutrition_data:
            logger.debug(
                f"No nutrition data found in search result for food: {food_item.get('description', 'Unknown')}"
            )

        return nutrition

    def get_usage_stats(self) -> Dict:
        """Get service usage statistics"""
        return {
            "api_keys_count": len(self.api_keys),
            "current_key_index": self.current_key_index,
            "is_available": self.is_available(),
        }


# Global service instance
_usda_service = None


def get_usda_service() -> USDANutritionService:
    """Get global USDA service instance"""
    global _usda_service
    if _usda_service is None:
        _usda_service = USDANutritionService()
    return _usda_service
