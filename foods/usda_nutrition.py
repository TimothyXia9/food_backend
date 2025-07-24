"""
USDA FoodData Central API client
Query food nutrition information using USDA API keys
"""

import json
import requests
import time
import os
from typing import Dict, List, Any, Optional


class USDANutritionAPI:
    """USDA FoodData Central API client with key rotation"""

    def __init__(self):
        # Load API key from environment
        api_key = os.getenv("USDA_API_KEY")

        if not api_key:
            # Try loading multiple keys if available
            api_keys_str = os.getenv("USDA_API_KEYS", "[]")
            try:
                self.api_keys = json.loads(api_keys_str)
            except json.JSONDecodeError:
                raise ValueError("USDA_API_KEYS must be a valid JSON array")

            if not self.api_keys:
                raise ValueError(
                    "No USDA API keys found in environment variables (USDA_API_KEY or USDA_API_KEYS)"
                )
        else:
            self.api_keys = [api_key]

        self.current_key_index = 0
        self.base_url = "https://api.nal.usda.gov/fdc/v1"

    def get_current_api_key(self):
        """Get current API key"""
        return self.api_keys[self.current_key_index]

    def rotate_api_key(self):
        """Rotate to next API key"""
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)

    def search_foods(
        self, query: str, page_size: int = 25, page_number: int = 1
    ) -> Optional[Dict[str, Any]]:
        """
        Search for foods in USDA database

        Args:
                query (str): Search query
                page_size (int): Number of results per page (max 200)
                page_number (int): Page number (starts from 1)

        Returns:
                dict: Search results from USDA API
        """
        url = f"{self.base_url}/foods/search"
        params = {
            "api_key": self.get_current_api_key(),
            "query": query,
            "pageSize": page_size,
            "pageNumber": page_number,
            "dataType": ["Foundation", "SR Legacy"],  # Focus on basic foods
            "sortBy": "dataType.keyword",
            "sortOrder": "asc",
        }

        try:
            response = requests.get(url, params=params, timeout=30)

            # Handle rate limiting
            if response.status_code == 429:
                self.rotate_api_key()
                params["api_key"] = self.get_current_api_key()
                time.sleep(1)  # Brief delay before retry
                response = requests.get(url, params=params, timeout=30)

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException:
            return None

    def get_food_details(
        self, fdc_id: int, nutrients: Optional[List[int]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed nutrition information for a specific food

        Args:
                fdc_id (int): Food Data Central ID
                nutrients (list): List of nutrient IDs to retrieve (optional)

        Returns:
                dict: Detailed food information
        """
        url = f"{self.base_url}/food/{fdc_id}"
        params = {"api_key": self.get_current_api_key()}

        if nutrients:
            params["nutrients"] = nutrients

        try:
            response = requests.get(url, params=params, timeout=30)

            # Handle rate limiting
            if response.status_code == 429:
                self.rotate_api_key()
                params["api_key"] = self.get_current_api_key()
                time.sleep(1)  # Brief delay before retry
                response = requests.get(url, params=params, timeout=30)

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException:
            return None


def format_nutrition_info(
    food_data: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Format nutrition information for display"""
    if not food_data:
        return None

    # Extract basic information
    info = {
        "food_description": food_data.get("description", "N/A"),
        "fdc_id": food_data.get("fdcId", "N/A"),
        "data_type": food_data.get("dataType", "N/A"),
        "publication_date": food_data.get("publicationDate", "N/A"),
        "nutrients": {},
    }

    # Key nutrients we care about - mapped to consistent names
    key_nutrients = {
        1008: "calories",  # Energy (kcal)
        1003: "protein",  # Protein (g)
        1004: "fat",  # Total lipid (fat) (g)
        1005: "carbs",  # Carbohydrate, by difference (g)
        1079: "fiber",  # Fiber, total dietary (g)
        2000: "sugar",  # Sugars, total including NLEA (g)
        1087: "calcium",  # Calcium, Ca (mg)
        1089: "iron",  # Iron, Fe (mg)
        1092: "potassium",  # Potassium, K (mg)
        1093: "sodium",  # Sodium, Na (mg)
        1104: "vitamin_a",  # Vitamin A, IU (IU)
        1162: "vitamin_c",  # Vitamin C, total ascorbic acid (mg)
    }

    # Extract nutrition data
    food_nutrients = food_data.get("foodNutrients", [])
    for nutrient in food_nutrients:
        nutrient_id = nutrient.get("nutrient", {}).get("id")
        if nutrient_id in key_nutrients:
            nutrient_key = key_nutrients[nutrient_id]
            amount = nutrient.get("amount", 0)
            info["nutrients"][nutrient_key] = amount

    return info
