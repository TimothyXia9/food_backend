"""
Food Data Service
Handles food database operations and USDA integration
"""

import logging
from typing import Dict, List, Any, Optional
from django.db.models import Q
from django.core.paginator import Paginator
from decimal import Decimal

from .models import Food, FoodAlias, FoodSearchLog

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
                    if food.get("gtinUpc") == barcode or barcode in food.get("description", ""):
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
