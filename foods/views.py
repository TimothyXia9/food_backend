"""
Food API views
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
import logging

from .models import Food, FoodAlias, FoodSearchLog
from .serializers import (
    FoodSerializer,
    FoodSearchSerializer,
    USDAFoodSearchSerializer,
    USDANutritionSerializer,
    CreateFoodFromUSDASerializer,
    CustomFoodSerializer,
    FoodSearchLogSerializer,
)
from .usda_service import get_usda_service

logger = logging.getLogger(__name__)


@api_view(["GET"])
@permission_classes([AllowAny])
def search_foods(request):
    """Search for foods - now uses USDA as primary source with local fallback"""

    try:
        # Get search parameters
        query = request.GET.get("query", "").strip()
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 20))

        if not query:
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Query parameter is required",
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Try USDA search first
        from .usda_service import get_usda_service

        usda_service = get_usda_service()

        if usda_service.is_available():
            # Search USDA database
            result = usda_service.search_foods(query, min(page_size, 25), page)

            if result["success"]:
                # Format the results for our API
                foods_data = []
                for food in result.get("foods", []):
                    # Get complete food name with brand if available
                    food_name = food.get("description", "")
                    brand_owner = food.get("brandOwner", "")

                    # Create a more complete name
                    if brand_owner and brand_owner.lower() not in food_name.lower():
                        display_name = f"{brand_owner} - {food_name}"
                    else:
                        display_name = food_name

                    # Extract nutrition data from search result
                    nutrition = usda_service._extract_nutrition_from_search_result(food)

                    food_data = {
                        "id": food.get("fdcId"),
                        "fdc_id": food.get("fdcId"),
                        "name": display_name,
                        "brand": brand_owner,
                        "data_type": food.get("dataType"),
                        "publication_date": food.get("publicationDate"),
                        "is_usda": True,
                        "category": {"name": "USDA Food"},
                        "serving_size": 100,
                        "is_custom": False,
                    }

                    # Add nutrition data
                    food_data.update(nutrition)
                    foods_data.append(food_data)

                # Log the search
                if request.user.is_authenticated:
                    try:
                        FoodSearchLog.objects.create(
                            user=request.user,
                            search_query=query,
                            search_type="text",
                            results_count=len(foods_data),
                        )
                    except Exception as e:
                        print(f"Warning: Could not log search: {e}")

                return Response(
                    {
                        "success": True,
                        "data": {
                            "foods": foods_data,
                            "total_count": result.get("total_hits", len(foods_data)),
                            "page": page,
                            "page_size": page_size,
                            "total_pages": max(
                                1,
                                (
                                    result.get("total_hits", len(foods_data))
                                    + page_size
                                    - 1
                                )
                                // page_size,
                            ),
                            "source": "USDA",
                        },
                    },
                    status=status.HTTP_200_OK,
                )

        # Fallback to local search if USDA is not available
        from django.db.models import Q

        foods_queryset = (
            Food.objects.filter(
                Q(name__icontains=query) | Q(aliases__alias__icontains=query)
            )
            .select_related("created_by")
            .distinct()
            .order_by("name")
        )

        # Pagination
        total_count = foods_queryset.count()
        total_pages = (total_count + page_size - 1) // page_size
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        foods = foods_queryset[start_index:end_index]

        # Serialize the results
        foods_data = []
        for food in foods:
            foods_data.append(
                {
                    "id": food.id,
                    "name": food.name,
                    "brand": food.brand,
                    "calories_per_100g": float(food.calories_per_100g),
                    "protein_per_100g": (
                        float(food.protein_per_100g) if food.protein_per_100g else None
                    ),
                    "fat_per_100g": (
                        float(food.fat_per_100g) if food.fat_per_100g else None
                    ),
                    "carbs_per_100g": (
                        float(food.carbs_per_100g) if food.carbs_per_100g else None
                    ),
                    "fiber_per_100g": (
                        float(food.fiber_per_100g) if food.fiber_per_100g else None
                    ),
                    "sugar_per_100g": (
                        float(food.sugar_per_100g) if food.sugar_per_100g else None
                    ),
                    "sodium_per_100g": (
                        float(food.sodium_per_100g) if food.sodium_per_100g else None
                    ),
                    "serving_size": float(food.serving_size),
                    "is_custom": food.is_custom,
                    "is_verified": food.is_verified,
                    "is_usda": False,
                    "category": {
                        "name": "Custom Food" if food.is_custom else "Standard Food"
                    },
                }
            )

        # Log the search
        if request.user.is_authenticated:
            try:
                FoodSearchLog.objects.create(
                    user=request.user,
                    search_query=query,
                    search_type="text",
                    results_count=total_count,
                )
            except Exception as log_error:
                logger.warning(f"Failed to log search: {log_error}")

        return Response(
            {
                "success": True,
                "data": {
                    "foods": foods_data,
                    "total_count": total_count,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": total_pages,
                    "source": "LOCAL",
                },
                "message": f"Found {total_count} foods matching '{query}'",
            }
        )

    except ValueError as e:
        return Response(
            {
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid page or page_size parameter",
                },
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        logger.error(f"Error in search_foods: {e}")
        return Response(
            {
                "success": False,
                "error": {
                    "code": "SERVER_ERROR",
                    "message": "An error occurred while searching foods",
                },
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_food_details(request, food_id):
    """Get detailed information about a specific food"""

    try:
        food = Food.objects.select_related("created_by").get(id=food_id)

        food_data = {
            "id": food.id,
            "name": food.name,
            "brand": food.brand,
            "barcode": food.barcode,
            "category": {
                "id": 1 if food.is_custom else 2,
                "name": "Custom Food" if food.is_custom else "Standard Food",
            },
            "serving_size": float(food.serving_size),
            "calories_per_100g": float(food.calories_per_100g),
            "protein_per_100g": (
                float(food.protein_per_100g) if food.protein_per_100g else None
            ),
            "fat_per_100g": float(food.fat_per_100g) if food.fat_per_100g else None,
            "carbs_per_100g": (
                float(food.carbs_per_100g) if food.carbs_per_100g else None
            ),
            "fiber_per_100g": (
                float(food.fiber_per_100g) if food.fiber_per_100g else None
            ),
            "sugar_per_100g": (
                float(food.sugar_per_100g) if food.sugar_per_100g else None
            ),
            "sodium_per_100g": (
                float(food.sodium_per_100g) if food.sodium_per_100g else None
            ),
            "is_custom": food.is_custom,
            "is_verified": food.is_verified,
            "created_by": food.created_by.username if food.created_by else None,
            "created_at": food.created_at.isoformat(),
            "updated_at": food.updated_at.isoformat(),
        }

        return Response(
            {
                "success": True,
                "data": food_data,
                "message": f"Retrieved details for {food.name}",
            }
        )

    except Food.DoesNotExist:
        return Response(
            {
                "success": False,
                "error": {"code": "NOT_FOUND", "message": "Food not found"},
            },
            status=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        logger.error(f"Error in get_food_details: {e}")
        return Response(
            {
                "success": False,
                "error": {
                    "code": "SERVER_ERROR",
                    "message": "An error occurred while getting food details",
                },
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def search_usda_foods(request):
    """Search USDA FoodData Central database"""

    try:
        # Get search parameters
        query = request.GET.get("query", "").strip()
        page_size = int(request.GET.get("page_size", 25))
        page_number = int(request.GET.get("page", 1))

        if not query:
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Query parameter is required",
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get USDA service
        usda_service = get_usda_service()

        if not usda_service.is_available():
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "SERVICE_UNAVAILABLE",
                        "message": "USDA API service is not configured. Please add USDA_API_KEY to environment variables.",
                    },
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # Search USDA database
        result = usda_service.search_foods(query, page_size, page_number)

        if result["success"]:
            # Format the results for our API
            foods_data = []
            for food in result.get("foods", []):
                foods_data.append(
                    {
                        "fdc_id": food.get("fdcId"),
                        "description": food.get("description"),
                        "data_type": food.get("dataType"),
                        "publication_date": food.get("publicationDate"),
                        "brand_owner": food.get("brandOwner"),
                        "ingredients": food.get("ingredients"),
                        "score": food.get("score", 0),
                    }
                )

            return Response(
                {
                    "success": True,
                    "data": {
                        "foods": foods_data,
                        "total_hits": result.get("total_hits", 0),
                        "current_page": result.get("current_page", page_number),
                        "total_pages": result.get("total_pages", 1),
                        "query": query,
                    },
                    "message": f"Found {result.get('total_hits', 0)} USDA foods matching '{query}'",
                }
            )
        else:
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "USDA_API_ERROR",
                        "message": result.get("error", "USDA search failed"),
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    except ValueError as e:
        return Response(
            {
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid page or page_size parameter",
                },
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        logger.error(f"Error in search_usda_foods: {e}")
        return Response(
            {
                "success": False,
                "error": {
                    "code": "SERVER_ERROR",
                    "message": "An error occurred while searching USDA foods",
                },
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def get_usda_nutrition(request, fdc_id):
    """Get detailed nutrition information from USDA"""

    try:
        # Get USDA service
        usda_service = get_usda_service()

        if not usda_service.is_available():
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "SERVICE_UNAVAILABLE",
                        "message": "USDA API service is not configured",
                    },
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # Get nutrition details
        result = usda_service.get_food_details(int(fdc_id))

        if result["success"]:
            nutrition_data = result["nutrition_data"]

            # Format the nutrition data to match our API structure
            formatted_data = {
                "id": nutrition_data.get("fdc_id"),
                "fdc_id": nutrition_data.get("fdc_id"),
                "name": nutrition_data.get("description"),
                "brand": nutrition_data.get("brand_owner", ""),
                "data_type": nutrition_data.get("data_type"),
                "publication_date": nutrition_data.get("publication_date"),
                "is_usda": True,
                "calories_per_100g": nutrition_data.get("calories_per_100g", 0),
                "protein_per_100g": nutrition_data.get("protein_per_100g", 0),
                "fat_per_100g": nutrition_data.get("fat_per_100g", 0),
                "carbs_per_100g": nutrition_data.get("carbs_per_100g", 0),
                "fiber_per_100g": nutrition_data.get("fiber_per_100g", 0),
                "sugar_per_100g": nutrition_data.get("sugar_per_100g", 0),
                "sodium_per_100g": nutrition_data.get("sodium_per_100g", 0),
                "category": {"name": "USDA Food"},
                "serving_size": 100,
                "is_custom": False,
                "is_verified": True,
                "ingredients": nutrition_data.get("ingredients", ""),
                "nutrients": nutrition_data.get("nutrients", []),
            }

            return Response(
                {
                    "success": True,
                    "data": formatted_data,
                    "message": f"Retrieved nutrition data for FDC ID {fdc_id}",
                }
            )
        else:
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "USDA_API_ERROR",
                        "message": result.get("error", "Nutrition data not found"),
                    },
                },
                status=status.HTTP_404_NOT_FOUND,
            )

    except ValueError as e:
        return Response(
            {
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid FDC ID format",
                },
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        logger.error(f"Error in get_usda_nutrition: {e}")
        return Response(
            {
                "success": False,
                "error": {
                    "code": "SERVER_ERROR",
                    "message": "An error occurred while getting nutrition data",
                },
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_food_from_usda(request):
    """Create a food record from USDA data"""

    try:
        fdc_id = request.data.get("fdc_id")
        if not fdc_id:
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "fdc_id is required",
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get USDA service
        usda_service = get_usda_service()

        if not usda_service.is_available():
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "SERVICE_UNAVAILABLE",
                        "message": "USDA API service is not configured",
                    },
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # Get nutrition data from USDA
        result = usda_service.get_food_details(int(fdc_id))

        if not result["success"]:
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "USDA_API_ERROR",
                        "message": result.get("error", "Failed to get USDA data"),
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        nutrition_data = result["nutrition_data"]
        nutrients = nutrition_data.get("nutrients", {})

        # Create food record
        food = Food.objects.create(
            name=nutrition_data.get("description", f"USDA Food {fdc_id}"),
            serving_size=100,  # USDA data is per 100g
            calories_per_100g=nutrients.get("calories", {}).get("amount", 0),
            protein_per_100g=nutrients.get("protein", {}).get("amount"),
            fat_per_100g=nutrients.get("fat", {}).get("amount"),
            carbs_per_100g=nutrients.get("carbs", {}).get("amount"),
            fiber_per_100g=nutrients.get("fiber", {}).get("amount"),
            sugar_per_100g=nutrients.get("sugar", {}).get("amount"),
            sodium_per_100g=nutrients.get("sodium", {}).get("amount"),
            is_verified=True,  # USDA data is verified
            created_by=request.user,
        )

        return Response(
            {
                "success": True,
                "data": {"food_id": food.id, "name": food.name, "fdc_id": fdc_id},
                "message": f"Successfully created food from USDA data (FDC ID: {fdc_id})",
            },
            status=status.HTTP_201_CREATED,
        )

    except ValueError as e:
        return Response(
            {
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid FDC ID format",
                },
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        logger.error(f"Error in create_food_from_usda: {e}")
        return Response(
            {
                "success": False,
                "error": {
                    "code": "SERVER_ERROR",
                    "message": "An error occurred while creating food from USDA data",
                },
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_custom_food(request):
    """Create a custom food record"""

    try:
        serializer = CustomFoodSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Invalid data provided",
                        "details": serializer.errors,
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        validated_data = serializer.validated_data
        aliases = validated_data.pop("aliases", [])

        # Create the food record
        food = Food.objects.create(
            name=validated_data["name"],
            brand=validated_data.get("brand", ""),
            barcode=validated_data.get("barcode", ""),
            serving_size=validated_data["serving_size"],
            calories_per_100g=validated_data["calories_per_100g"],
            protein_per_100g=validated_data["protein_per_100g"],
            fat_per_100g=validated_data["fat_per_100g"],
            carbs_per_100g=validated_data["carbs_per_100g"],
            fiber_per_100g=validated_data["fiber_per_100g"],
            sugar_per_100g=validated_data["sugar_per_100g"],
            sodium_per_100g=validated_data["sodium_per_100g"],
            is_verified=False,  # Custom foods are not verified by default
            created_by=request.user,
        )

        # Create aliases if provided
        if aliases:
            for alias in aliases:
                if alias.strip():
                    FoodAlias.objects.create(food=food, alias=alias.strip())

        # Return the created food data
        food_data = {
            "id": food.id,
            "name": food.name,
            "brand": food.brand,
            "barcode": food.barcode,
            "serving_size": float(food.serving_size),
            "calories_per_100g": float(food.calories_per_100g),
            "protein_per_100g": float(food.protein_per_100g),
            "fat_per_100g": float(food.fat_per_100g),
            "carbs_per_100g": float(food.carbs_per_100g),
            "fiber_per_100g": float(food.fiber_per_100g),
            "sugar_per_100g": float(food.sugar_per_100g),
            "sodium_per_100g": float(food.sodium_per_100g),
            "is_custom": True,
            "is_verified": food.is_verified,
            "created_by": request.user.username,
            "created_at": food.created_at.isoformat(),
            "aliases": aliases,
        }

        return Response(
            {
                "success": True,
                "data": food_data,
                "message": f'Custom food "{food.name}" created successfully',
            },
            status=status.HTTP_201_CREATED,
        )

    except Exception as e:
        logger.error(f"Error in create_custom_food: {e}")
        return Response(
            {
                "success": False,
                "error": {
                    "code": "SERVER_ERROR",
                    "message": "An error occurred while creating the custom food",
                },
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_food(request, food_id):
    """Update a food record"""

    try:
        # Check if food exists and user can edit it
        try:
            food = Food.objects.get(id=food_id, created_by=request.user)
        except Food.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "NOT_FOUND",
                        "message": "Food not found or you do not have permission to edit it",
                    },
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # Validate the data
        serializer = CustomFoodSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Invalid data provided",
                        "details": serializer.errors,
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        validated_data = serializer.validated_data
        aliases = validated_data.pop("aliases", [])

        # Update the food record
        for field, value in validated_data.items():
            setattr(food, field, value)
        food.save()

        # Update aliases
        # Remove existing aliases
        food.aliases.all().delete()

        # Create new aliases
        if aliases:
            for alias in aliases:
                if alias.strip():
                    FoodAlias.objects.create(food=food, alias=alias.strip())

        # Return updated food data
        food_data = {
            "id": food.id,
            "name": food.name,
            "brand": food.brand,
            "barcode": food.barcode,
            "serving_size": float(food.serving_size),
            "calories_per_100g": float(food.calories_per_100g),
            "protein_per_100g": float(food.protein_per_100g),
            "fat_per_100g": float(food.fat_per_100g),
            "carbs_per_100g": float(food.carbs_per_100g),
            "fiber_per_100g": float(food.fiber_per_100g),
            "sugar_per_100g": float(food.sugar_per_100g),
            "sodium_per_100g": float(food.sodium_per_100g),
            "is_custom": True,
            "is_verified": food.is_verified,
            "created_by": request.user.username,
            "updated_at": food.updated_at.isoformat(),
            "aliases": aliases,
        }

        return Response(
            {
                "success": True,
                "data": food_data,
                "message": f'Food "{food.name}" updated successfully',
            },
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        logger.error(f"Error in update_food: {e}")
        return Response(
            {
                "success": False,
                "error": {
                    "code": "SERVER_ERROR",
                    "message": "An error occurred while updating the food",
                },
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_food(request, food_id):
    """Delete a custom food record"""

    try:
        # Check if food exists and user can delete it
        try:
            food = Food.objects.get(id=food_id, created_by=request.user)
        except Food.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "NOT_FOUND",
                        "message": "Food not found or you do not have permission to delete it",
                    },
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check if food is used in any meals and remove from them
        from meals.models import MealFood

        meal_foods = MealFood.objects.filter(food=food)
        meal_count = 0
        meal_foods_count = 0

        if meal_foods.exists():
            # Get meal information for notification
            meal_count = meal_foods.values("meal").distinct().count()
            meal_foods_count = meal_foods.count()

            # Remove this food from all meals
            meal_foods.delete()

        food_name = food.name
        food.delete()

        # Create response message based on whether food was removed from meals
        if meal_count > 0:
            message = f'Food "{food_name}" deleted successfully. It was removed from {meal_foods_count} meal entries across {meal_count} different meals.'
        else:
            message = f'Food "{food_name}" deleted successfully'

        return Response(
            {
                "success": True,
                "data": {
                    "removed_from_meals": meal_count > 0,
                    "meal_count": meal_count,
                    "meal_foods_count": meal_foods_count,
                },
                "message": message,
            },
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        logger.error(f"Error in delete_food: {e}")
        return Response(
            {
                "success": False,
                "error": {
                    "code": "SERVER_ERROR",
                    "message": "An error occurred while deleting the food",
                },
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_user_foods(request):
    """Get user's custom foods"""

    try:
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 20))

        # Get user's custom foods
        foods_queryset = (
            Food.objects.filter(created_by=request.user)
            .select_related("created_by")
            .order_by("-created_at")
        )

        # Pagination
        total_count = foods_queryset.count()
        total_pages = (total_count + page_size - 1) // page_size
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        foods = foods_queryset[start_index:end_index]

        # Serialize the results
        foods_data = []
        for food in foods:
            foods_data.append(
                {
                    "id": food.id,
                    "name": food.name,
                    "brand": food.brand,
                    "calories_per_100g": float(food.calories_per_100g),
                    "protein_per_100g": (
                        float(food.protein_per_100g) if food.protein_per_100g else None
                    ),
                    "fat_per_100g": (
                        float(food.fat_per_100g) if food.fat_per_100g else None
                    ),
                    "carbs_per_100g": (
                        float(food.carbs_per_100g) if food.carbs_per_100g else None
                    ),
                    "fiber_per_100g": (
                        float(food.fiber_per_100g) if food.fiber_per_100g else None
                    ),
                    "sugar_per_100g": (
                        float(food.sugar_per_100g) if food.sugar_per_100g else None
                    ),
                    "sodium_per_100g": (
                        float(food.sodium_per_100g) if food.sodium_per_100g else None
                    ),
                    "serving_size": float(food.serving_size),
                    "is_custom": True,
                    "is_verified": food.is_verified,
                    "is_usda": False,
                    "category": {"name": "Custom Food"},
                    "created_at": food.created_at.isoformat(),
                }
            )

        return Response(
            {
                "success": True,
                "data": {
                    "foods": foods_data,
                    "total_count": total_count,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": total_pages,
                    "source": "USER_CUSTOM",
                },
                "message": f"Found {total_count} custom foods",
            }
        )

    except ValueError as e:
        return Response(
            {
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid page or page_size parameter",
                },
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        logger.error(f"Error in get_user_foods: {e}")
        return Response(
            {
                "success": False,
                "error": {
                    "code": "SERVER_ERROR",
                    "message": "An error occurred while getting user foods",
                },
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_search_history(request):
    """Get user's search history"""

    try:
        limit = int(request.GET.get("limit", 20))

        # Get user's search history
        search_logs = FoodSearchLog.objects.filter(user=request.user).order_by(
            "-created_at"
        )[:limit]

        # Serialize the data
        searches = []
        for log in search_logs:
            searches.append(
                {
                    "id": log.id,
                    "search_query": log.search_query,
                    "search_type": log.search_type,
                    "results_count": log.results_count,
                    "created_at": log.created_at.isoformat(),
                }
            )

        return Response({"success": True, "data": {"searches": searches}})

    except ValueError:
        return Response(
            {
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid limit parameter",
                },
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        logger.error(f"Error in get_search_history: {e}")
        return Response(
            {
                "success": False,
                "error": {
                    "code": "SERVER_ERROR",
                    "message": "An error occurred while getting search history",
                },
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
