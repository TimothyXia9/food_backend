"""
Food Data Service
Handles food database operations and USDA integration
"""

import logging
import requests
from typing import Dict, List, Any, Optional
from django.db.models import Q
from django.core.paginator import Paginator
from decimal import Decimal

from .models import Food, FoodAlias, FoodSearchLog, UserFood

# Import USDA service
from .usda_nutrition import USDANutritionAPI, format_nutrition_info

logger = logging.getLogger(__name__)


class FoodDataService:
    """Service for managing food data and USDA integration"""

    def __init__(self):
        try:
            self.usda_service = USDANutritionAPI()
        except Exception as e:
            logger.warning(f"Failed to initialize USDA service: {e}")
            self.usda_service = None

    def search_foods(
        self, query: str, user_id: int = None, page: int = 1, page_size: int = 20
    ) -> Dict[str, Any]:
        """
        Search for foods in the database

        Args:
                query: Search query string
                user_id: Optional user ID for logging
                page: Page number for pagination
                page_size: Number of results per page

        Returns:
                Dictionary with search results
        """
        try:
            # Build search query
            search_query = Q(name__icontains=query)

            # Also search in aliases
            search_query |= Q(aliases__alias__icontains=query)

            # Get foods
            foods = Food.objects.filter(search_query).distinct().order_by("name")

            # Paginate results
            paginator = Paginator(foods, page_size)
            page_obj = paginator.get_page(page)

            # Format results
            results = []
            for food in page_obj.object_list:
                results.append(
                    {
                        "id": food.id,
                        "name": food.name,
                        "category": food.category.name if food.category else None,
                        "brand": food.brand,
                        "serving_size": float(food.serving_size),
                        "calories_per_100g": float(food.calories_per_100g),
                        "protein_per_100g": float(food.protein_per_100g or 0),
                        "fat_per_100g": float(food.fat_per_100g or 0),
                        "carbs_per_100g": float(food.carbs_per_100g or 0),
                        "fiber_per_100g": float(food.fiber_per_100g or 0),
                        "is_verified": food.is_verified,
                        "is_custom": food.is_custom,
                    }
                )

            # Log search
            if user_id:
                FoodSearchLog.objects.create(
                    user_id=user_id,
                    search_query=query,
                    results_count=len(results),
                    search_type="text",
                )

            return {
                "success": True,
                "query": query,
                "results": results,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_pages": paginator.num_pages,
                    "total_results": paginator.count,
                    "has_next": page_obj.has_next(),
                    "has_previous": page_obj.has_previous(),
                },
            }

        except Exception as e:
            logger.error(f"Food search failed: {str(e)}")
            return {"success": False, "error": str(e), "query": query}

    def get_food_details(self, food_id: int) -> Dict[str, Any]:
        """Get detailed information about a food"""

        try:
            food = Food.objects.get(id=food_id)

            # Get aliases
            aliases = [alias.alias for alias in food.aliases.all()]

            return {
                "success": True,
                "food": {
                    "id": food.id,
                    "name": food.name,
                    "category": food.category.name if food.category else None,
                    "brand": food.brand,
                    "barcode": food.barcode,
                    "serving_size": float(food.serving_size),
                    "calories_per_100g": float(food.calories_per_100g),
                    "protein_per_100g": float(food.protein_per_100g or 0),
                    "fat_per_100g": float(food.fat_per_100g or 0),
                    "carbs_per_100g": float(food.carbs_per_100g or 0),
                    "fiber_per_100g": float(food.fiber_per_100g or 0),
                    "sugar_per_100g": float(food.sugar_per_100g or 0),
                    "sodium_per_100g": float(food.sodium_per_100g or 0),
                    "is_verified": food.is_verified,
                    "is_custom": food.is_custom,
                    "aliases": aliases,
                    "created_at": food.created_at.isoformat(),
                    "updated_at": food.updated_at.isoformat(),
                },
            }

        except Food.DoesNotExist:
            return {"success": False, "error": "Food not found"}
        except Exception as e:
            logger.error(f"Failed to get food details: {str(e)}")
            return {"success": False, "error": str(e)}

    def search_usda_foods(self, query: str, page_size: int = 25) -> Dict[str, Any]:
        """Search USDA FoodData Central database"""

        try:
            results = self.usda_service.search_foods(query, page_size=page_size)

            if results and results.get("foods"):
                foods = results["foods"]
                formatted_foods = []

                for food in foods:
                    formatted_foods.append(
                        {
                            "fdc_id": food.get("fdcId"),
                            "description": food.get("description"),
                            "data_type": food.get("dataType"),
                            "brand_owner": food.get("brandOwner", ""),
                            "ingredients": food.get("ingredients", ""),
                        }
                    )

                return {
                    "success": True,
                    "total_results": len(formatted_foods),
                    "foods": formatted_foods,
                }
            else:
                return {
                    "success": False,
                    "message": f"No results found for query: {query}",
                }

        except Exception as e:
            logger.error(f"USDA search failed: {str(e)}")
            return {"success": False, "error": str(e)}

    def search_usda_by_barcode(self, barcode: str) -> Dict[str, Any]:
        """Search USDA FoodData Central database by barcode/UPC"""

        try:
            # USDA API supports UPC lookup through the search endpoint
            results = self.usda_service.search_foods(barcode, page_size=10)

            if results and results.get("foods"):
                foods = results["foods"]
                barcode_foods = []

                for food in foods:
                    # Filter for foods that are likely UPC matches
                    if food.get("gtinUpc") == barcode or barcode in food.get(
                        "description", ""
                    ):
                        barcode_foods.append(
                            {
                                "fdc_id": food.get("fdcId"),
                                "description": food.get("description"),
                                "data_type": food.get("dataType"),
                                "brand_owner": food.get("brandOwner", ""),
                                "ingredients": food.get("ingredients", ""),
                                "gtin_upc": food.get("gtinUpc", ""),
                                "serving_size": food.get("servingSize", ""),
                                "serving_size_unit": food.get("servingSizeUnit", ""),
                            }
                        )

                if barcode_foods:
                    return {
                        "success": True,
                        "barcode": barcode,
                        "total_results": len(barcode_foods),
                        "foods": barcode_foods,
                    }
                else:
                    return {
                        "success": False,
                        "message": f"No USDA products found for barcode: {barcode}",
                        "barcode": barcode,
                    }
            else:
                return {
                    "success": False,
                    "message": f"No results found for barcode: {barcode}",
                    "barcode": barcode,
                }

        except Exception as e:
            logger.error(f"USDA barcode search failed: {str(e)}")
            return {"success": False, "error": str(e), "barcode": barcode}

    def get_usda_nutrition(self, fdc_id: int) -> Dict[str, Any]:
        """Get detailed nutrition information from USDA"""

        try:
            detailed_info = self.usda_service.get_food_details(fdc_id)
            nutrition_info = format_nutrition_info(detailed_info)

            if nutrition_info:
                return {"success": True, "nutrition_data": nutrition_info}
            else:
                return {
                    "success": False,
                    "message": f"No nutrition data found for FDC ID: {fdc_id}",
                }

        except Exception as e:
            logger.error(f"USDA nutrition lookup failed: {str(e)}")
            return {"success": False, "error": str(e)}

    def create_food_from_usda(self, fdc_id: int, user_id: int = None) -> Dict[str, Any]:
        """Create a food record from USDA data"""

        try:
            # Get USDA nutrition data
            usda_result = self.get_usda_nutrition(fdc_id)

            if not usda_result["success"]:
                return usda_result

            nutrition_data = usda_result["nutrition_data"]

            # Check if food already exists
            usda_description = nutrition_data.get("food_description", "")
            existing_food = Food.objects.filter(name=usda_description).first()

            if existing_food:
                return {
                    "success": True,
                    "food_id": existing_food.id,
                    "message": "Food already exists",
                }

            # No category needed

            # Create food record
            nutrients = nutrition_data.get("nutrients", {})

            food = Food.objects.create(
                name=usda_description,
                serving_size=Decimal("100.00"),
                calories_per_100g=Decimal(str(nutrients.get("calories", 0))),
                protein_per_100g=Decimal(str(nutrients.get("protein", 0))),
                fat_per_100g=Decimal(str(nutrients.get("fat", 0))),
                carbs_per_100g=Decimal(str(nutrients.get("carbs", 0))),
                fiber_per_100g=Decimal(str(nutrients.get("fiber", 0))),
                sugar_per_100g=Decimal(str(nutrients.get("sugar", 0))),
                sodium_per_100g=Decimal(str(nutrients.get("sodium", 0))),
                is_verified=True,
                created_by_id=user_id,
            )

            return {
                "success": True,
                "food_id": food.id,
                "message": "Food created successfully",
            }

        except Exception as e:
            logger.error(f"Failed to create food from USDA: {str(e)}")
            return {"success": False, "error": str(e)}

    def create_custom_food(
        self, food_data: Dict[str, Any], user_id: int
    ) -> Dict[str, Any]:
        """Create a custom food record"""

        try:
            # Create food record
            food = Food.objects.create(
                name=food_data["name"],
                brand=food_data.get("brand", ""),
                barcode=food_data.get("barcode", ""),
                serving_size=Decimal(str(food_data.get("serving_size", 100))),
                calories_per_100g=Decimal(str(food_data["calories_per_100g"])),
                protein_per_100g=Decimal(str(food_data.get("protein_per_100g", 0))),
                fat_per_100g=Decimal(str(food_data.get("fat_per_100g", 0))),
                carbs_per_100g=Decimal(str(food_data.get("carbs_per_100g", 0))),
                fiber_per_100g=Decimal(str(food_data.get("fiber_per_100g", 0))),
                sugar_per_100g=Decimal(str(food_data.get("sugar_per_100g", 0))),
                sodium_per_100g=Decimal(str(food_data.get("sodium_per_100g", 0))),
                is_verified=False,
                created_by_id=user_id,
            )

            # Add aliases if provided
            if food_data.get("aliases"):
                for alias in food_data["aliases"]:
                    FoodAlias.objects.create(food=food, alias=alias.strip())

            return {
                "success": True,
                "food_id": food.id,
                "message": "Custom food created successfully",
            }

        except Exception as e:
            logger.error(f"Failed to create custom food: {str(e)}")
            return {"success": False, "error": str(e)}

    def update_food(
        self, food_id: int, food_data: Dict[str, Any], user_id: int
    ) -> Dict[str, Any]:
        """Update a food record"""

        try:
            food = Food.objects.get(id=food_id)

            # Check if user can edit this food
            if food.created_by_id and food.created_by_id != user_id:
                return {
                    "success": False,
                    "error": "You can only edit foods you created",
                }

            # Update fields
            for field, value in food_data.items():
                if hasattr(food, field):
                    if field in [
                        "serving_size",
                        "calories_per_100g",
                        "protein_per_100g",
                        "fat_per_100g",
                        "carbs_per_100g",
                        "fiber_per_100g",
                        "sugar_per_100g",
                        "sodium_per_100g",
                    ]:
                        setattr(food, field, Decimal(str(value)))
                    else:
                        setattr(food, field, value)

            food.save()

            return {
                "success": True,
                "food_id": food_id,
                "message": "Food updated successfully",
            }

        except Food.DoesNotExist:
            return {"success": False, "error": "Food not found"}
        except Exception as e:
            logger.error(f"Failed to update food: {str(e)}")
            return {"success": False, "error": str(e)}

    def delete_food(self, food_id: int, user_id: int) -> Dict[str, Any]:
        """Delete a custom food record"""

        try:
            food = Food.objects.get(id=food_id)

            # Check if user can delete this food
            if food.created_by_id != user_id:
                return {
                    "success": False,
                    "error": "You can only delete foods you created",
                }

            food.delete()

            return {"success": True, "message": "Food deleted successfully"}

        except Food.DoesNotExist:
            return {"success": False, "error": "Food not found"}
        except Exception as e:
            logger.error(f"Failed to delete food: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_user_search_history(self, user_id: int, limit: int = 20) -> Dict[str, Any]:
        """Get user's search history"""

        try:
            searches = FoodSearchLog.objects.filter(user_id=user_id).order_by(
                "-created_at"
            )[:limit]

            results = []
            for search in searches:
                results.append(
                    {
                        "query": search.search_query,
                        "search_type": search.search_type,
                        "results_count": search.results_count,
                        "created_at": search.created_at.isoformat(),
                    }
                )

            return {"success": True, "searches": results}

        except Exception as e:
            logger.error(f"Failed to get search history: {str(e)}")
            return {"success": False, "error": str(e)}

    def search_openfoodfacts_by_barcode(self, barcode: str) -> Dict[str, Any]:
        """
        Search Open Food Facts database by barcode

        Args:
            barcode: Product barcode/UPC code

        Returns:
            Dictionary with product information and nutrition data
        """
        try:
            # Open Food Facts API endpoint
            url = f"https://world.openfoodfacts.org/api/v3/product/{barcode}.json"

            headers = {
                "Content-Type": "application/json",
                "User-Agent": "CalorieTracker/1.0 (https://yourapp.com)",
            }

            logger.info(f"Searching Open Food Facts for barcode: {barcode}")
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()

                # Check if product was found (API v3 format)
                if (
                    data.get("status") in ["success", "success_with_warnings"]
                    and "product" in data
                    and data["product"]
                ):
                    product = data["product"]

                    # Extract nutrition information
                    nutriments = product.get("nutriments", {})

                    # Format nutrition data (per 100g when available)
                    nutrition_per_100g = self._extract_openfoodfacts_nutrition(
                        nutriments
                    )

                    # Extract basic product info (API v3 format)
                    ecoscore_grade = product.get("ecoscore_grade", "")

                    product_info = {
                        "barcode": barcode,
                        "product_name": product.get("product_name", ""),
                        "product_name_en": product.get("product_name_en", ""),
                        "brands": product.get("brands", ""),
                        "categories": product.get("categories", ""),
                        "ingredients_text": product.get("ingredients_text", ""),
                        "serving_size": product.get("serving_size", ""),
                        "serving_quantity": product.get("serving_quantity", ""),
                        "nutrition_grade": product.get(
                            "nutriscore_grade", product.get("nutrition_grade_fr", "")
                        ),
                        "ecoscore_grade": ecoscore_grade,
                        "image_url": product.get("image_url", ""),
                        "image_front_url": product.get("image_front_url", ""),
                        "image_small_url": product.get("image_small_url", ""),
                        "nutrition_per_100g": nutrition_per_100g,
                        "data_source": "Open Food Facts",
                    }

                    return {
                        "success": True,
                        "product": product_info,
                        "message": f"Found product: {product_info['product_name']}",
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Product with barcode {barcode} not found in Open Food Facts database",
                    }
            else:
                return {
                    "success": False,
                    "message": f"Open Food Facts API error: {response.status_code}",
                }

        except requests.exceptions.Timeout:
            logger.error(
                f"Timeout when searching Open Food Facts for barcode: {barcode}"
            )
            return {
                "success": False,
                "message": "Request timeout when searching Open Food Facts",
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error when searching Open Food Facts: {str(e)}")
            return {"success": False, "message": f"Network error: {str(e)}"}
        except Exception as e:
            logger.error(f"Error searching Open Food Facts: {str(e)}")
            return {"success": False, "message": f"Search error: {str(e)}"}

    def _extract_openfoodfacts_nutrition(
        self, nutriments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract and format nutrition data from Open Food Facts nutriments

        Args:
            nutriments: Raw nutriments data from Open Food Facts

        Returns:
            Formatted nutrition data per 100g
        """
        try:
            # Map Open Food Facts nutrient names to standard names (API v3 format)
            nutrition_mapping = {
                "energy-kcal_100g": "calories",
                "energy-kcal": "calories",  # Fallback for v3
                "energy_100g": "energy_kj",
                "proteins_100g": "protein",
                "proteins": "protein",  # Fallback for v3
                "carbohydrates_100g": "carbohydrates",
                "carbohydrates": "carbohydrates",  # Fallback for v3
                "sugars_100g": "sugars",
                "sugars": "sugars",  # Fallback for v3
                "fat_100g": "fat",
                "fat": "fat",  # Fallback for v3
                "saturated-fat_100g": "saturated_fat",
                "saturated-fat": "saturated_fat",  # Fallback for v3
                "fiber_100g": "fiber",
                "fiber": "fiber",  # Fallback for v3
                "sodium_100g": "sodium",
                "sodium": "sodium",  # Fallback for v3
                "salt_100g": "salt",
                "salt": "salt",  # Fallback for v3
            }

            nutrition_data = {}

            for off_key, standard_key in nutrition_mapping.items():
                value = nutriments.get(off_key)
                if value is not None:
                    try:
                        nutrition_data[standard_key] = float(value)
                    except (ValueError, TypeError):
                        pass

            # Convert sodium to milligrams if available
            if "sodium" in nutrition_data:
                nutrition_data["sodium_mg"] = nutrition_data["sodium"] * 1000

            # Add additional nutrients if available
            additional_nutrients = [
                "cholesterol_100g",
                "vitamin-c_100g",
                "calcium_100g",
                "iron_100g",
                "vitamin-a_100g",
                "vitamin-d_100g",
            ]

            for nutrient in additional_nutrients:
                value = nutriments.get(nutrient)
                if value is not None:
                    try:
                        # Remove the _100g suffix for clean key names
                        clean_key = nutrient.replace("_100g", "").replace("-", "_")
                        nutrition_data[clean_key] = float(value)
                    except (ValueError, TypeError):
                        pass

            return nutrition_data

        except Exception as e:
            logger.error(f"Error extracting Open Food Facts nutrition: {str(e)}")
            return {}

    def search_barcode_combined(self, barcode: str) -> Dict[str, Any]:
        """
        Search for barcode in both USDA and Open Food Facts databases

        Args:
            barcode: Product barcode/UPC code

        Returns:
            Combined results from both databases
        """
        try:
            results = {
                "barcode": barcode,
                "usda_results": [],
                "openfoodfacts_result": None,
                "total_sources": 0,
            }

            # Search USDA database
            if self.usda_service:
                usda_result = self.search_usda_by_barcode(barcode)
                if usda_result.get("success") and usda_result.get("foods"):
                    results["usda_results"] = usda_result["foods"]
                    results["total_sources"] += 1

            # Search Open Food Facts
            off_result = self.search_openfoodfacts_by_barcode(barcode)
            if off_result.get("success") and off_result.get("product"):
                results["openfoodfacts_result"] = off_result["product"]
                results["total_sources"] += 1

            return {
                "success": True,
                "data": results,
                "message": f"Found product information from {results['total_sources']} source(s)",
            }

        except Exception as e:
            logger.error(f"Error in combined barcode search: {str(e)}")
            return {"success": False, "message": f"Combined search error: {str(e)}"}

    def create_food_from_barcode(self, barcode: str, user_id: int) -> Dict[str, Any]:
        """
        Create a Food object from barcode scan results, or return existing food if barcode already exists

        Args:
            barcode: Product barcode/UPC code
            user_id: ID of the user creating the food

        Returns:
            Dictionary with created or existing Food object information
        """
        try:
            # Check if food with this barcode already exists
            existing_food = Food.objects.filter(barcode=barcode).first()
            if existing_food:
                # Create or get the UserFood association for this user
                user_food, created = UserFood.objects.get_or_create(
                    user_id=user_id, food=existing_food
                )

                return {
                    "success": True,
                    "food": {
                        "id": existing_food.id,
                        "name": existing_food.name,
                        "brand": existing_food.brand or "",
                        "barcode": existing_food.barcode or "",
                        "serving_size": float(existing_food.serving_size),
                        "serving_unit": "g",
                        "calories_per_100g": float(existing_food.calories_per_100g),
                        "protein_per_100g": float(existing_food.protein_per_100g or 0),
                        "fat_per_100g": float(existing_food.fat_per_100g or 0),
                        "carbs_per_100g": float(existing_food.carbs_per_100g or 0),
                        "fiber_per_100g": float(existing_food.fiber_per_100g or 0),
                        "sugar_per_100g": float(existing_food.sugar_per_100g or 0),
                        "sodium_per_100g": float(existing_food.sodium_per_100g or 0),
                        "description": f"Product with barcode {barcode}",
                        "ingredients": "",
                        "data_source": "Existing Database",
                        "nutrition_grade": "",
                        "image_url": "",
                    },
                    "message": (
                        f"Added existing food with barcode {barcode} to your list: {existing_food.name}"
                        if created
                        else f"Food with barcode {barcode} already in your list: {existing_food.name}"
                    ),
                    "is_existing": True,
                    "newly_added": created,
                }

            # No existing food found, proceed with creation
            # First try Open Food Facts
            off_result = self.search_openfoodfacts_by_barcode(barcode)

            if off_result.get("success") and off_result.get("product"):
                product = off_result["product"]
                nutrition = product.get("nutrition_per_100g", {})

                # Create Food object from Open Food Facts data (only use fields that exist in model)
                food_data = {
                    "name": product.get("product_name")
                    or product.get("product_name_en")
                    or f"Product {barcode}",
                    "brand": (
                        product.get("brands", "").split(",")[0].strip()
                        if product.get("brands")
                        else ""
                    ),
                    "serving_size": 100,  # Default to 100g
                    "calories_per_100g": nutrition.get("calories", 0),
                    "protein_per_100g": nutrition.get("protein", 0),
                    "fat_per_100g": nutrition.get("fat", 0),
                    "carbs_per_100g": nutrition.get("carbohydrates", 0),
                    "fiber_per_100g": nutrition.get("fiber", 0),
                    "sugar_per_100g": nutrition.get("sugars", 0),
                    "sodium_per_100g": nutrition.get("sodium", 0),
                    "barcode": barcode,
                    "created_by_id": user_id,
                    "is_verified": False,  # Mark as unverified since it's from external source
                }

                # Create the food
                food = Food.objects.create(**food_data)

                # Create UserFood association for this user
                UserFood.objects.create(user_id=user_id, food=food)

                return {
                    "success": True,
                    "food": {
                        "id": food.id,
                        "name": food.name,
                        "brand": food.brand or "",
                        "barcode": food.barcode or "",
                        "serving_size": float(food.serving_size),
                        "serving_unit": "g",  # Default unit
                        "calories_per_100g": float(food.calories_per_100g),
                        "protein_per_100g": float(food.protein_per_100g or 0),
                        "fat_per_100g": float(food.fat_per_100g or 0),
                        "carbs_per_100g": float(food.carbs_per_100g or 0),
                        "fiber_per_100g": float(food.fiber_per_100g or 0),
                        "sugar_per_100g": float(food.sugar_per_100g or 0),
                        "sodium_per_100g": float(food.sodium_per_100g or 0),
                        "description": f"Product scanned from barcode {barcode}",
                        "ingredients": product.get("ingredients_text", "")[:500],
                        "data_source": "Open Food Facts",
                        "nutrition_grade": product.get("nutrition_grade", ""),
                        "image_url": product.get("image_front_url", ""),
                    },
                    "message": f"Created food from barcode: {food.name}",
                }

            # Fallback to USDA if available
            elif self.usda_service:
                usda_result = self.search_usda_by_barcode(barcode)
                if usda_result.get("success") and usda_result.get("foods"):
                    # Use first USDA result
                    usda_food = usda_result["foods"][0]

                    # Get detailed nutrition from USDA
                    nutrition_result = self.get_usda_nutrition(usda_food["fdc_id"])
                    nutrition_data = (
                        nutrition_result.get("nutrition_data", {})
                        if nutrition_result.get("success")
                        else {}
                    )

                    food_data = {
                        "name": usda_food.get("description", f"Product {barcode}"),
                        "brand": usda_food.get("brand_owner", ""),
                        "serving_size": 100,  # Default to 100g
                        "calories_per_100g": nutrition_data.get("calories", 0),
                        "protein_per_100g": nutrition_data.get("protein", 0),
                        "fat_per_100g": nutrition_data.get("total_fat", 0),
                        "carbs_per_100g": nutrition_data.get("carbohydrates", 0),
                        "fiber_per_100g": nutrition_data.get("fiber", 0),
                        "sugar_per_100g": nutrition_data.get("sugars", 0),
                        "sodium_per_100g": nutrition_data.get("sodium", 0),
                        "barcode": barcode,
                        "created_by_id": user_id,
                        "is_verified": True,  # USDA data is more reliable
                    }

                    food = Food.objects.create(**food_data)

                    # Create UserFood association for this user
                    UserFood.objects.create(user_id=user_id, food=food)

                    return {
                        "success": True,
                        "food": {
                            "id": food.id,
                            "name": food.name,
                            "brand": food.brand or "",
                            "barcode": food.barcode or "",
                            "serving_size": float(food.serving_size),
                            "serving_unit": "g",  # Default unit
                            "calories_per_100g": float(food.calories_per_100g),
                            "protein_per_100g": float(food.protein_per_100g or 0),
                            "fat_per_100g": float(food.fat_per_100g or 0),
                            "carbs_per_100g": float(food.carbs_per_100g or 0),
                            "fiber_per_100g": float(food.fiber_per_100g or 0),
                            "sugar_per_100g": float(food.sugar_per_100g or 0),
                            "sodium_per_100g": float(food.sodium_per_100g or 0),
                            "description": f"Product scanned from barcode {barcode}",
                            "ingredients": usda_food.get("ingredients", "")[:500],
                            "data_source": "USDA",
                        },
                        "message": f"Created food from USDA data: {food.name}",
                    }

            # No product found
            return {
                "success": False,
                "message": f"No product found for barcode {barcode} in any database",
            }

        except Exception as e:
            logger.error(f"Error creating food from barcode {barcode}: {str(e)}")
            return {"success": False, "message": f"Error creating food: {str(e)}"}
