"""
Test script for USDA FoodData Central API
Query food nutrition information using USDA API keys
"""

import json
import requests
import time
from decouple import config
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class USDANutritionAPI:
    """USDA FoodData Central API client with key rotation"""

    def __init__(self):
        # Load API keys from environment
        api_keys_str = config("USDA_API_KEYS", default="[]", cast=str)
        try:
            self.api_keys = json.loads(api_keys_str)
        except json.JSONDecodeError:
            raise ValueError("USDA_API_KEYS must be a valid JSON array")

        if not self.api_keys:
            raise ValueError("No USDA API keys found in environment variables")

        self.current_key_index = 0
        self.base_url = "https://api.nal.usda.gov/fdc/v1"

    def get_current_api_key(self):
        """Get current API key"""
        return self.api_keys[self.current_key_index]

    def rotate_api_key(self):
        """Rotate to next API key"""
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        print(
            f"🔄 Rotated to API key {self.current_key_index + 1}/{len(self.api_keys)}"
        )

    def search_foods(self, query, page_size=25, page_number=1):
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
                print("⚠️  Rate limit reached, rotating API key...")
                self.rotate_api_key()
                params["api_key"] = self.get_current_api_key()
                time.sleep(1)  # Brief delay before retry
                response = requests.get(url, params=params, timeout=30)

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"❌ API request failed: {e}")
            return None

    def get_food_details(self, fdc_id, nutrients=None):
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
                print("⚠️  Rate limit reached, rotating API key...")
                self.rotate_api_key()
                params["api_key"] = self.get_current_api_key()
                time.sleep(1)  # Brief delay before retry
                response = requests.get(url, params=params, timeout=30)

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"❌ API request failed: {e}")
            return None


def format_nutrition_info(food_data):
    """Format nutrition information for display"""
    if not food_data:
        return None

    # Extract basic information
    info = {
        "description": food_data.get("description", "N/A"),
        "fdc_id": food_data.get("fdcId", "N/A"),
        "data_type": food_data.get("dataType", "N/A"),
        "publication_date": food_data.get("publicationDate", "N/A"),
        "nutrients": {},
    }

    # Key nutrients we care about
    key_nutrients = {
        1008: "Energy (kcal)",
        1003: "Protein (g)",
        1004: "Total lipid (fat) (g)",
        1005: "Carbohydrate, by difference (g)",
        1079: "Fiber, total dietary (g)",
        2000: "Sugars, total including NLEA (g)",
        1087: "Calcium, Ca (mg)",
        1089: "Iron, Fe (mg)",
        1092: "Potassium, K (mg)",
        1093: "Sodium, Na (mg)",
        1104: "Vitamin A, IU (IU)",
        1162: "Vitamin C, total ascorbic acid (mg)",
    }

    # Extract nutrition data
    food_nutrients = food_data.get("foodNutrients", [])
    for nutrient in food_nutrients:
        nutrient_id = nutrient.get("nutrient", {}).get("id")
        if nutrient_id in key_nutrients:
            nutrient_name = key_nutrients[nutrient_id]
            amount = nutrient.get("amount", 0)
            info["nutrients"][nutrient_name] = amount

    return info


def test_food_search(api_client, queries):
    """Test food search functionality"""
    print("🔍 Testing USDA Food Search")
    print("=" * 50)

    for query in queries:
        print(f"\n📝 Searching for: '{query}'")
        print("-" * 30)

        results = api_client.search_foods(query, page_size=5)

        if results and results.get("foods"):
            foods = results["foods"]
            print(f"✅ Found {len(foods)} results (showing first {min(5, len(foods))})")

            for i, food in enumerate(foods[:5], 1):
                print(
                    f"{i}. {food.get('description', 'N/A')} (ID: {food.get('fdcId', 'N/A')})"
                )
        else:
            print("❌ No results found or API error")


def test_nutrition_details(api_client, fdc_ids):
    """Test detailed nutrition information retrieval"""
    print("\n📊 Testing Nutrition Details")
    print("=" * 50)

    for fdc_id in fdc_ids:
        print(f"\n🥗 Getting nutrition info for FDC ID: {fdc_id}")
        print("-" * 40)

        food_data = api_client.get_food_details(fdc_id)
        nutrition_info = format_nutrition_info(food_data)

        if nutrition_info:
            print(f"✅ Food: {nutrition_info['description']}")
            print(f"   Type: {nutrition_info['data_type']}")
            print(f"   Date: {nutrition_info['publication_date']}")
            print("   Key Nutrients (per 100g):")

            for nutrient, amount in nutrition_info["nutrients"].items():
                print(f"     • {nutrient}: {amount}")
        else:
            print("❌ Failed to get nutrition information")


def main():
    """Main test function"""
    print("🥙 USDA Nutrition API Test")
    print("=" * 50)

    try:
        # Initialize API client
        api_client = USDANutritionAPI()
        print(f"✅ Initialized with {len(api_client.api_keys)} API key(s)")

        # Test queries
        test_queries = ["apple", "chicken breast", "brown rice", "broccoli", "salmon"]

        # Test search functionality
        test_food_search(api_client, test_queries)

        # Test specific food IDs (common foods)
        test_fdc_ids = [
            171688,  # Apple, raw
            171077,  # Chicken, broilers or fryers, breast, meat only, raw
            168880,  # Rice, brown, long-grain, raw
            170379,  # Broccoli, raw
            175167,  # Fish, salmon, Atlantic, farmed, raw
        ]

        # Test detailed nutrition
        test_nutrition_details(api_client, test_fdc_ids)

        print("\n🎉 Testing completed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")


if __name__ == "__main__":
    main()
