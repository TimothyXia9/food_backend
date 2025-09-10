"""
Image API views for food recognition
"""

import asyncio
import os
import json
from PIL import Image
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    permission_classes,
    authentication_classes,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.response import Response
from django.core.files.storage import default_storage
from django.utils import timezone
from django.http import StreamingHttpResponse
from asgiref.sync import sync_to_async
import logging

from .models import UploadedImage, FoodRecognitionResult
from .serializers import (
    UploadedImageSerializer,
    ImageUploadSerializer,
    FoodRecognitionResultSerializer,
    ImageAnalysisRequestSerializer,
    ConfirmFoodRecognitionSerializer,
    CreateMealFromImageSerializer,
    BarcodeDetectionRequestSerializer,
    BarcodeDetectionResultSerializer,
    USDABarcodeSearchSerializer,
    USDABarcodeResultSerializer,
)
from .services import FoodImageAnalysisService
from .barcode_service import BarcodeDetectionService
from foods.services import FoodDataService
from foods.models import Food, UserFood

logger = logging.getLogger(__name__)


def clean_json_response(content: str) -> str:
    """
    清理OpenAI响应中的JSON，移除可能的代码块标记
    """
    cleaned_content = content.strip()

    # 移除各种可能的代码块标记
    if cleaned_content.startswith("```json"):
        cleaned_content = cleaned_content[7:]
    elif cleaned_content.startswith("```"):
        cleaned_content = cleaned_content[3:]

    if cleaned_content.endswith("```"):
        cleaned_content = cleaned_content[:-3]

    return cleaned_content.strip()


def get_default_nutrition_data() -> dict:
    """
    获取默认营养数据
    """
    return {
        "calories_per_100g": 100,
        "protein_per_100g": 10,
        "fat_per_100g": 5,
        "carbs_per_100g": 20,
        "fiber_per_100g": 2,
        "sugar_per_100g": 5,
        "sodium_per_100g": 100,
    }


def create_default_nutrition_dict(
    food_name: str, description: str = "Nutrition data not available"
) -> dict:
    """
    创建包含默认营养数据的完整字典
    """
    nutrition_dict = {
        "food_name": food_name,
        "usda_description": description,
        "fdc_id": None,
    }
    nutrition_dict.update(get_default_nutrition_data())
    return nutrition_dict


def process_stage1_foods_response(
    stage1_data: dict, enhance_with_usda: bool = True
) -> list:
    """
    Process Stage 1 OpenAI response and convert to standardized format

    Args:
        stage1_data: Raw JSON response from OpenAI
        enhance_with_usda: Whether to enhance with USDA search terms (ignored, kept for compatibility)

    Returns:
        List of standardized food items with bilingual support
    """
    if "foods" in stage1_data and isinstance(stage1_data["foods"], list):
        # Convert to backward compatible format while preserving new data
        processed_foods = []
        for food in stage1_data["foods"]:
            # Use English name directly for USDA search if available, fallback to Chinese name
            chinese_name = food.get("name_chinese", food.get("name", "未知食物"))
            english_name = food.get("name_english", "")
            usda_search_term = english_name if english_name else chinese_name

            food_item = {
                # Backward compatibility - use Chinese name as primary name
                "name": chinese_name,
                "confidence": food.get("confidence", 0.8),
                # New bilingual fields
                "name_chinese": chinese_name,
                "name_english": english_name,
                "usda_search_term": usda_search_term,
                "category": food.get("category", "other"),
            }
            processed_foods.append(food_item)
        return processed_foods
    else:
        # 如果JSON格式不正确，尝试解析为简单列表
        food_names = [
            item.get("name", item.get("name_chinese", "未知食物"))
            for item in stage1_data.get("foods", [])
        ]
        return [
            {
                "name": name,
                "confidence": 0.8,
                "name_chinese": name,
                "name_english": "",
                "usda_search_term": name,
                "category": "other",
            }
            for name in food_names[:5]
        ]


def update_food_nutrition(food_obj: Food, nutrition_data: dict) -> None:
    """
    使用营养数据更新Food对象的营养字段
    """
    defaults = get_default_nutrition_data()

    food_obj.calories_per_100g = nutrition_data.get(
        "calories_per_100g", defaults["calories_per_100g"]
    )
    food_obj.protein_per_100g = nutrition_data.get(
        "protein_per_100g", defaults["protein_per_100g"]
    )
    food_obj.fat_per_100g = nutrition_data.get("fat_per_100g", defaults["fat_per_100g"])
    food_obj.carbs_per_100g = nutrition_data.get(
        "carbs_per_100g", defaults["carbs_per_100g"]
    )
    food_obj.fiber_per_100g = nutrition_data.get(
        "fiber_per_100g", defaults["fiber_per_100g"]
    )
    food_obj.sugar_per_100g = nutrition_data.get(
        "sugar_per_100g", defaults["sugar_per_100g"]
    )
    food_obj.sodium_per_100g = nutrition_data.get(
        "sodium_per_100g", defaults["sodium_per_100g"]
    )


def get_food_nutrition_kwargs(nutrition_data: dict) -> dict:
    """
    从营养数据字典获取Food模型创建时需要的营养字段kwargs
    """
    defaults = get_default_nutrition_data()
    return {
        "calories_per_100g": nutrition_data.get(
            "calories_per_100g", defaults["calories_per_100g"]
        ),
        "protein_per_100g": nutrition_data.get(
            "protein_per_100g", defaults["protein_per_100g"]
        ),
        "fat_per_100g": nutrition_data.get("fat_per_100g", defaults["fat_per_100g"]),
        "carbs_per_100g": nutrition_data.get(
            "carbs_per_100g", defaults["carbs_per_100g"]
        ),
        "fiber_per_100g": nutrition_data.get(
            "fiber_per_100g", defaults["fiber_per_100g"]
        ),
        "sugar_per_100g": nutrition_data.get(
            "sugar_per_100g", defaults["sugar_per_100g"]
        ),
        "sodium_per_100g": nutrition_data.get(
            "sodium_per_100g", defaults["sodium_per_100g"]
        ),
    }


def create_user_food_from_recognition(user_id: int, nutrition_data: dict) -> dict:
    """
    从图像识别结果创建用户自定义食物

    Args:
        user_id: 用户ID
        nutrition_data: 营养数据字典，包含食物名称和营养成分

    Returns:
        dict: 创建结果，包含食物ID和状态
    """
    try:
        from django.contrib.auth import get_user_model

        User = get_user_model()

        user = User.objects.get(id=user_id)
        food_name = nutrition_data.get("food_name", "Unknown Food")

        # 检查是否已存在相同名称的食物（由同一用户创建）
        existing_food = Food.objects.filter(
            name__iexact=food_name, created_by=user
        ).first()

        if existing_food:
            # 如果已存在，更新营养数据（使用最新的识别结果）
            update_food_nutrition(existing_food, nutrition_data)

            # 更新USDA信息
            if nutrition_data.get("fdc_id"):
                existing_food.usda_fdc_id = str(nutrition_data.get("fdc_id"))

            existing_food.save()

            # 确保在用户食物库中
            user_food, created = UserFood.objects.get_or_create(
                user=user, food=existing_food
            )

            return {
                "success": True,
                "food_id": existing_food.id,
                "is_new": False,
                "message": f"Updated existing food: {food_name}",
                "food_data": {
                    "id": existing_food.id,
                    "name": existing_food.name,
                    "calories_per_100g": float(existing_food.calories_per_100g),
                    "protein_per_100g": float(existing_food.protein_per_100g or 0),
                    "fat_per_100g": float(existing_food.fat_per_100g or 0),
                    "carbs_per_100g": float(existing_food.carbs_per_100g or 0),
                    "fiber_per_100g": float(existing_food.fiber_per_100g or 0),
                    "sugar_per_100g": float(existing_food.sugar_per_100g or 0),
                    "sodium_per_100g": float(existing_food.sodium_per_100g or 0),
                    "is_custom": True,
                    "usda_fdc_id": existing_food.usda_fdc_id,
                },
            }
        else:
            # 创建新的用户食物
            nutrition_kwargs = get_food_nutrition_kwargs(nutrition_data)
            new_food = Food.objects.create(
                name=food_name,
                serving_size=100,  # 默认100g
                created_by=user,
                is_verified=False,
                usda_fdc_id=(
                    str(nutrition_data.get("fdc_id"))
                    if nutrition_data.get("fdc_id")
                    else None
                ),
                **nutrition_kwargs,
            )

            # 添加到用户食物库
            UserFood.objects.create(user=user, food=new_food)

            return {
                "success": True,
                "food_id": new_food.id,
                "is_new": True,
                "message": f"Created new food: {food_name}",
                "food_data": {
                    "id": new_food.id,
                    "name": new_food.name,
                    "calories_per_100g": float(new_food.calories_per_100g),
                    "protein_per_100g": float(new_food.protein_per_100g or 0),
                    "fat_per_100g": float(new_food.fat_per_100g or 0),
                    "carbs_per_100g": float(new_food.carbs_per_100g or 0),
                    "fiber_per_100g": float(new_food.fiber_per_100g or 0),
                    "sugar_per_100g": float(new_food.sugar_per_100g or 0),
                    "sodium_per_100g": float(new_food.sodium_per_100g or 0),
                    "is_custom": True,
                    "usda_fdc_id": new_food.usda_fdc_id,
                },
            }

    except Exception as e:
        logger.error(f"Error creating user food from recognition: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "food_id": None,
            "is_new": False,
            "message": f"Failed to create food: {str(e)}",
        }


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_image(request):
    """Upload an image for food recognition"""

    serializer = ImageUploadSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"success": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        image_file = serializer.validated_data["image"]
        meal_id = serializer.validated_data.get("meal_id")

        # Get image dimensions
        pil_image = Image.open(image_file)
        width, height = pil_image.size

        # Create image record
        uploaded_image = UploadedImage.objects.create(
            user=request.user,
            meal_id=meal_id,
            filename=image_file.name,
            file_path=image_file,
            file_size=image_file.size,
            mime_type=image_file.content_type,
            width=width,
            height=height,
            processing_status="pending",
        )

        # Serialize response
        serializer = UploadedImageSerializer(uploaded_image)

        return Response(
            {
                "success": True,
                "data": serializer.data,
                "message": "Image uploaded successfully",
            },
            status=status.HTTP_201_CREATED,
        )

    except Exception as e:
        logger.error(f"Image upload failed: {str(e)}")
        return Response(
            {"success": False, "message": f"Image upload failed: {str(e)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )


def analyze_food_image_two_stage(image_path: str) -> dict:
    """
    两段式食物图像分析函数
    第一阶段：识别食物种类
    第二阶段：估算每种食物的分量
    返回JSON格式的结果
    """
    try:
        # 首先检查文件是否存在
        if not os.path.exists(image_path):
            logger.error(f"Image file not found: {image_path}")
            return {
                "success": False,
                "error": "图片文件未找到",
                "stage_1": {"food_types": []},
                "stage_2": {"food_portions": []},
            }

        from calorie_tracker.openai_service import get_openai_service
        import base64
        import requests
        import json

        # 读取图片并转换为base64
        with open(image_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode("utf-8")

        service = get_openai_service()

        # Import prompts management
        from .prompts import FoodAnalysisPrompts

        # 第一阶段：识别食物种类
        logger.info(f"Stage 1: Identifying food types in image: {image_path}")

        stage1_prompt = FoodAnalysisPrompts.get_food_identification_prompt()

        # 构造第一阶段消息
        stage1_messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": stage1_prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_data}"},
                    },
                ],
            }
        ]

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {service._get_current_api_key()}",
        }

        payload = {
            "model": "gpt-4o",
            "messages": stage1_messages,
            "max_tokens": 200,
            "temperature": 0.1,
        }

        # 调用第一阶段API
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
        )

        stage1_result = {"food_types": []}

        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"].strip()
            logger.info(f"Stage 1 OpenAI response: {content}")

            try:
                # 清理响应内容，移除可能的代码块标记
                cleaned_content = clean_json_response(content)

                # 尝试解析JSON
                stage1_data = json.loads(cleaned_content)
                stage1_result["food_types"] = process_stage1_foods_response(
                    stage1_data, enhance_with_usda=True
                )
            except json.JSONDecodeError:
                # 如果JSON解析失败，使用默认值
                logger.warning(f"Failed to parse Stage 1 JSON response: {content}")
                stage1_result["food_types"] = [
                    {
                        "name": "未识别食物",
                        "confidence": 0.5,
                        "name_chinese": "未识别食物",
                        "name_english": "unidentified food",
                        "usda_search_term": "unidentified food",
                        "category": "other",
                    }
                ]
        else:
            logger.error(
                f"Stage 1 OpenAI API error: {response.status_code} - {response.text}"
            )
            stage1_result["food_types"] = [
                {
                    "name": "未识别食物",
                    "confidence": 0.5,
                    "name_chinese": "未识别食物",
                    "name_english": "unidentified food",
                    "usda_search_term": "unidentified food",
                    "category": "other",
                }
            ]

        # 第二阶段：估算食物分量
        logger.info(
            f"Stage 2: Estimating food portions for {len(stage1_result['food_types'])} foods"
        )

        if not stage1_result["food_types"]:
            return {
                "success": True,
                "stage_1": stage1_result,
                "stage_2": {"food_portions": []},
            }

        # 构造食物列表用于第二阶段
        stage2_prompt = FoodAnalysisPrompts.get_portion_estimation_prompt(
            stage1_result["food_types"]
        )

        # 构造第二阶段消息
        stage2_messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": stage2_prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_data}"},
                    },
                ],
            }
        ]

        payload["messages"] = stage2_messages
        payload["max_tokens"] = 300

        # 调用第二阶段API
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
        )

        stage2_result = {"food_portions": []}

        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"].strip()
            logger.info(f"Stage 2 OpenAI response: {content}")

            try:
                # 清理响应内容，移除可能的代码块标记
                cleaned_content = clean_json_response(content)

                # 尝试解析JSON
                stage2_data = json.loads(cleaned_content)
                if "portions" in stage2_data and isinstance(
                    stage2_data["portions"], list
                ):
                    stage2_result["food_portions"] = stage2_data["portions"]
                else:
                    # 如果JSON格式不正确，使用默认估算
                    stage2_result["food_portions"] = [
                        {
                            "name": food["name"],
                            "estimated_grams": 100,
                            "portion_description": f"约100克{food['name']}",
                        }
                        for food in stage1_result["food_types"]
                    ]
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse Stage 2 JSON response: {content}")
                # 使用默认估算
                stage2_result["food_portions"] = [
                    {
                        "name": food["name"],
                        "estimated_grams": 100,
                        "portion_description": f"约100克{food['name']}",
                    }
                    for food in stage1_result["food_types"]
                ]
        else:
            logger.error(
                f"Stage 2 OpenAI API error: {response.status_code} - {response.text}"
            )
            # 使用默认估算
            stage2_result["food_portions"] = [
                {
                    "name": food["name"],
                    "estimated_grams": 100,
                    "portion_description": f"约100克{food['name']}",
                }
                for food in stage1_result["food_types"]
            ]

        # Stage 3: Get USDA nutrition data for identified foods using averaged top 10 results
        stage3_result = {"nutrition_data": []}

        try:
            from foods.usda_nutrition import (
                USDANutritionAPI,
                get_averaged_nutrition_from_top_results,
            )

            usda_service = USDANutritionAPI()

            for portion in stage2_result["food_portions"]:
                food_name = portion.get("name", "")
                if food_name:
                    # Find corresponding food from stage1 for better search terms
                    usda_search_term = food_name  # fallback
                    for food_type in stage1_result["food_types"]:
                        if (
                            food_type.get("name") == food_name
                            or food_type.get("name_chinese") == food_name
                        ):
                            # Prefer English name for better USDA search results
                            english_name = food_type.get("name_english", "")
                            if english_name and english_name.strip():
                                usda_search_term = english_name
                            else:
                                usda_search_term = food_type.get(
                                    "usda_search_term", food_name
                                )
                            break

                    # Search USDA for nutrition data using averaged top 10 results
                    logger.info(
                        f"Searching USDA for '{food_name}' using averaged term: '{usda_search_term}'"
                    )

                    # Get averaged nutrition from top 10 USDA results
                    averaged_result = get_averaged_nutrition_from_top_results(
                        usda_service, usda_search_term, top_count=10
                    )

                    if averaged_result and averaged_result.get("success"):
                        # Use the averaged nutrition data
                        avg_nutrition = averaged_result["averaged_nutrition"]

                        nutrition_info = {
                            "food_name": food_name,
                            "usda_description": f"Averaged from {averaged_result['valid_results_count']} USDA sources",
                            "fdc_id": f"averaged_from_{averaged_result['valid_results_count']}_sources",
                            "search_term_used": usda_search_term,
                            "source_count": averaged_result["valid_results_count"],
                            **avg_nutrition,  # Include all averaged nutrition values
                        }

                        # Log successful averaging
                        logger.info(
                            f"Successfully averaged nutrition for '{food_name}' from {averaged_result['valid_results_count']} USDA sources"
                        )

                        stage3_result["nutrition_data"].append(nutrition_info)
                    else:
                        # Fallback to single result if averaging fails
                        error_reason = averaged_result.get('error', 'Unknown error') if averaged_result else 'No result'
                        logger.warning(
                            f"Averaging failed for '{food_name}' (reason: {error_reason}), trying single result fallback"
                        )

                        usda_search_result = usda_service.search_foods(
                            usda_search_term, page_size=3
                        )

                        if usda_search_result and usda_search_result.get("foods"):
                            # Get the first (most relevant) result as fallback
                            first_food = usda_search_result["foods"][0]

                            # Get detailed nutrition data
                            nutrition_data = usda_service.get_food_details(
                                first_food.get("fdcId")
                            )

                            if nutrition_data:
                                # Extract key nutrition facts
                                nutrients = nutrition_data.get("foodNutrients", [])
                                nutrition_info = {
                                    "food_name": food_name,
                                    "usda_description": first_food.get(
                                        "description", ""
                                    ),
                                    "fdc_id": first_food.get("fdcId"),
                                    "search_term_used": usda_search_term,
                                    "source_count": 1,
                                    "calories_per_100g": 100,  # Default fallback
                                    "protein_per_100g": 10,
                                    "fat_per_100g": 5,
                                    "carbs_per_100g": 20,
                                    "fiber_per_100g": 2,
                                    "sugar_per_100g": 5,
                                    "sodium_per_100g": 100,
                                }

                                # Map USDA nutrient data
                                for nutrient in nutrients:
                                    nutrient_name = (
                                        nutrient.get("nutrient", {})
                                        .get("name", "")
                                        .lower()
                                    )
                                    amount = nutrient.get("amount", 0)

                                    if "energy" in nutrient_name and amount > 0:
                                        nutrition_info["calories_per_100g"] = round(
                                            amount, 1
                                        )
                                    elif "protein" in nutrient_name and amount > 0:
                                        nutrition_info["protein_per_100g"] = round(
                                            amount, 1
                                        )
                                    elif "total lipid" in nutrient_name and amount > 0:
                                        nutrition_info["fat_per_100g"] = round(
                                            amount, 1
                                        )
                                    elif (
                                        "carbohydrate" in nutrient_name
                                        and "by difference" in nutrient_name
                                        and amount > 0
                                    ):
                                        nutrition_info["carbs_per_100g"] = round(
                                            amount, 1
                                        )
                                    elif "fiber" in nutrient_name and amount > 0:
                                        nutrition_info["fiber_per_100g"] = round(
                                            amount, 1
                                        )
                                    elif "sugars" in nutrient_name and amount > 0:
                                        nutrition_info["sugar_per_100g"] = round(
                                            amount, 1
                                        )
                                    elif "sodium" in nutrient_name and amount > 0:
                                        nutrition_info["sodium_per_100g"] = round(
                                            amount, 1
                                        )

                                stage3_result["nutrition_data"].append(nutrition_info)
                            else:
                                # Add default nutrition data if USDA lookup fails
                                # Add default nutrition data if USDA lookup fails
                                logger.warning(f"USDA nutrition lookup failed for '{food_name}' - no detailed nutrition data available")
                                stage3_result["nutrition_data"].append(
                                    create_default_nutrition_dict(
                                        food_name, f"USDA lookup failed for {usda_search_term}"
                                    )
                                )
                        else:
                            # Add default nutrition data if USDA search fails completely
                            logger.warning(f"USDA search completely failed for '{food_name}' using term '{usda_search_term}' - no USDA records found")
                            stage3_result["nutrition_data"].append(
                                create_default_nutrition_dict(
                                    food_name, f"No USDA records found for {usda_search_term}"
                                )
                            )
        except Exception as e:
            logger.warning(f"USDA nutrition lookup failed: {str(e)}")
            # Add default nutrition data for all foods if USDA service fails
            for portion in stage2_result["food_portions"]:
                stage3_result["nutrition_data"].append(
                    create_default_nutrition_dict(
                        portion.get("name", "Unknown"), "USDA service unavailable"
                    )
                )

        return {
            "success": True,
            "stage_1": stage1_result,
            "stage_2": stage2_result,
            "stage_3": stage3_result,
        }

    except Exception as e:
        logger.error(f"Error in two-stage food analysis: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "stage_1": {"food_types": []},
            "stage_2": {"food_portions": []},
            "stage_3": {"nutrition_data": []},
        }


def get_food_keywords_from_image(image_path: str) -> list[str]:
    """
    兼容性函数，将新的两段式分析结果转换为原有的关键词列表格式
    保持向后兼容性
    """
    try:
        result = analyze_food_image_two_stage(image_path)
        if result["success"] and result["stage_1"]["food_types"]:
            return [food["name"] for food in result["stage_1"]["food_types"]]
        else:
            return ["苹果", "香蕉", "面包", "鸡肉", "米饭", "蔬菜"]
    except Exception as e:
        logger.error(f"Error in compatibility function: {str(e)}")
        return ["苹果", "香蕉", "面包", "鸡肉", "米饭", "蔬菜"]


def analyze_food_image_streaming(image_path: str, image_id: int):
    """
    流式输出的两段式食物图像分析
    使用生成器实现Server-Sent Events
    """
    try:
        # 首先检查文件是否存在
        if not os.path.exists(image_path):
            logger.error(f"Image file not found: {image_path}")
            yield f"data: {json.dumps({'error': '图片文件未找到', 'step': 'error'})}\n\n"
            return

        from calorie_tracker.openai_service import get_openai_service
        from .prompts import FoodAnalysisPrompts
        import base64
        import requests

        # 读取图片并转换为base64
        with open(image_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode("utf-8")

        service = get_openai_service()

        # 发送开始信号
        yield f"data: {json.dumps({'step': 'start', 'message': '开始分析图片', 'image_id': image_id})}\n\n"

        # 第一阶段：识别食物种类
        logger.info(f"Stage 1: Identifying food types in image: {image_path}")
        yield f"data: {json.dumps({'step': 'food_detection', 'message': '正在识别食物种类...', 'progress': 25})}\n\n"

        stage1_prompt = FoodAnalysisPrompts.get_streaming_food_identification_prompt()

        # 构造第一阶段消息
        stage1_messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": stage1_prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_data}"},
                    },
                ],
            }
        ]

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {service._get_current_api_key()}",
        }

        payload = {
            "model": "gpt-4o",
            "messages": stage1_messages,
            "max_tokens": 200,
            "temperature": 0.1,
        }

        # 调用第一阶段API
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
        )

        stage1_result = {"food_types": []}

        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"].strip()
            logger.info(f"Stage 1 OpenAI response: {content}")

            try:
                # 清理响应内容，移除可能的代码块标记
                cleaned_content = clean_json_response(content)

                # 尝试解析JSON
                stage1_data = json.loads(cleaned_content)
                stage1_result["food_types"] = process_stage1_foods_response(
                    stage1_data, enhance_with_usda=True
                )
            except json.JSONDecodeError:
                # 如果JSON解析失败，使用默认值
                logger.warning(f"Failed to parse Stage 1 JSON response: {content}")
                stage1_result["food_types"] = [
                    {
                        "name": "未识别食物",
                        "confidence": 0.5,
                        "name_chinese": "未识别食物",
                        "name_english": "unidentified food",
                        "usda_search_term": "unidentified food",
                        "category": "other",
                    }
                ]

            # 发送第一阶段结果
            yield f"data: {json.dumps({'step': 'food_detection_complete', 'foods': stage1_result['food_types'], 'progress': 50})}\n\n"
        else:
            logger.error(
                f"Stage 1 OpenAI API error: {response.status_code} - {response.text}"
            )
            stage1_result["food_types"] = [
                {"name": "苹果", "confidence": 0.6},
                {"name": "香蕉", "confidence": 0.6},
            ]
            yield f"data: {json.dumps({'step': 'food_detection_complete', 'foods': stage1_result['food_types'], 'progress': 50, 'warning': '使用默认食物'})}\n\n"

        # 第二阶段：估算食物分量
        logger.info(
            f"Stage 2: Estimating food portions for {len(stage1_result['food_types'])} foods"
        )
        yield f"data: {json.dumps({'step': 'portion_estimation', 'message': '正在估算食物分量...', 'progress': 75})}\n\n"

        if not stage1_result["food_types"]:
            yield f"data: {json.dumps({'step': 'complete', 'stage_1': stage1_result, 'stage_2': {'food_portions': []}, 'progress': 100})}\n\n"
            return

        # 构造食物列表用于第二阶段
        food_list = [food["name"] for food in stage1_result["food_types"]]
        food_names_str = "、".join(food_list)

        stage2_prompt = f"""基于图片中识别到的食物：{food_names_str}，请估算每种食物的大致分量(克数)。以JSON格式返回：
{{
	"portions": [
		{{"name": "米饭", "estimated_grams": 150, "cooking_method": "蒸"}},
		{{"name": "鸡胸肉", "estimated_grams": 120, "cooking_method": "煎"}}
	]
}}
请根据图片中食物的实际大小和常见分量进行估算。只返回JSON，不要添加其他说明文字。"""

        # 构造第二阶段消息
        stage2_messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": stage2_prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_data}"},
                    },
                ],
            }
        ]

        payload["messages"] = stage2_messages
        payload["max_tokens"] = 300

        # 调用第二阶段API
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
        )

        stage2_result = {"food_portions": []}

        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"].strip()
            logger.info(f"Stage 2 OpenAI response: {content}")

            try:
                # 清理响应内容，移除可能的代码块标记
                cleaned_content = clean_json_response(content)

                # 尝试解析JSON
                stage2_data = json.loads(cleaned_content)
                if "portions" in stage2_data and isinstance(
                    stage2_data["portions"], list
                ):
                    stage2_result["food_portions"] = stage2_data["portions"]
                else:
                    # 如果JSON格式不正确，使用默认估算
                    stage2_result["food_portions"] = [
                        {
                            "name": food["name"],
                            "estimated_grams": 100,
                            "portion_description": f"约100克{food['name']}",
                        }
                        for food in stage1_result["food_types"]
                    ]
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse Stage 2 JSON response: {content}")
                # 使用默认估算
                stage2_result["food_portions"] = [
                    {
                        "name": food["name"],
                        "estimated_grams": 100,
                        "portion_description": f"约100克{food['name']}",
                    }
                    for food in stage1_result["food_types"]
                ]
        else:
            logger.error(
                f"Stage 2 OpenAI API error: {response.status_code} - {response.text}"
            )
            # 使用默认估算
            stage2_result["food_portions"] = [
                {
                    "name": food["name"],
                    "estimated_grams": 100,
                    "portion_description": f"约100克{food['name']}",
                }
                for food in stage1_result["food_types"]
            ]

        # Stage 3: Get USDA nutrition data for identified foods using averaged top 10 results
        logger.info(
            f"Stage 3: Getting USDA nutrition for {len(stage2_result['food_portions'])} foods"
        )
        yield f"data: {json.dumps({'step': 'nutrition_lookup', 'message': '正在查询营养数据...', 'progress': 85})}\n\n"

        stage3_result = {"nutrition_data": []}

        try:
            from foods.usda_nutrition import (
                USDANutritionAPI,
                get_averaged_nutrition_from_top_results,
            )

            usda_service = USDANutritionAPI()

            for portion in stage2_result["food_portions"]:
                food_name = portion.get("name", "")
                if food_name:
                    # Find corresponding food from stage1 for better search terms
                    usda_search_term = food_name  # fallback
                    for food_type in stage1_result["food_types"]:
                        if (
                            food_type.get("name") == food_name
                            or food_type.get("name_chinese") == food_name
                        ):
                            # Prefer English name for better USDA search results
                            english_name = food_type.get("name_english", "")
                            if english_name and english_name.strip():
                                usda_search_term = english_name
                            else:
                                usda_search_term = food_type.get(
                                    "usda_search_term", food_name
                                )
                            break

                    # Get averaged nutrition from top 10 USDA results
                    averaged_result = get_averaged_nutrition_from_top_results(
                        usda_service, usda_search_term, top_count=10
                    )

                    if averaged_result and averaged_result.get("success"):
                        # Use the averaged nutrition data
                        avg_nutrition = averaged_result["averaged_nutrition"]

                        nutrition_info = {
                            "food_name": food_name,
                            "usda_description": f"Averaged from {averaged_result['valid_results_count']} USDA sources",
                            "fdc_id": f"averaged_from_{averaged_result['valid_results_count']}_sources",
                            "search_term_used": usda_search_term,
                            "source_count": averaged_result["valid_results_count"],
                            **avg_nutrition,  # Include all averaged nutrition values
                        }

                        stage3_result["nutrition_data"].append(nutrition_info)
                        logger.info(
                            f"Successfully averaged nutrition for '{food_name}' from {averaged_result['valid_results_count']} USDA sources"
                        )
                    else:
                        # Add default nutrition data if USDA search fails
                        error_reason = averaged_result.get('error', 'Unknown error') if averaged_result else 'No result'
                        logger.warning(f"USDA nutrition lookup failed for '{food_name}' using term '{usda_search_term}' - {error_reason}")
                        stage3_result["nutrition_data"].append(
                            create_default_nutrition_dict(
                                food_name, f"USDA search failed: {error_reason}"
                            )
                        )
        except Exception as e:
            logger.warning(f"USDA nutrition lookup failed: {str(e)}")
            # Add default nutrition data for all foods if USDA service fails
            for portion in stage2_result["food_portions"]:
                stage3_result["nutrition_data"].append(
                    create_default_nutrition_dict(
                        portion.get("name", "Unknown"), "USDA service unavailable"
                    )
                )

        # 发送最终结果
        final_result = {
            "step": "complete",
            "success": True,
            "stage_1": stage1_result,
            "stage_2": stage2_result,
            "stage_3": stage3_result,
            "progress": 100,
        }
        yield f"data: {json.dumps(final_result)}\n\n"

    except Exception as e:
        logger.error(f"Error in streaming food analysis: {str(e)}")
        yield f"data: {json.dumps({'step': 'error', 'error': str(e), 'progress': 0})}\n\n"


@api_view(["POST", "OPTIONS"])
def analyze_image_streaming(request):
    """流式分析图片的API端点"""

    # 处理预检请求
    if request.method == "OPTIONS":
        response = Response()
        response["Access-Control-Allow-Origin"] = "http://localhost:3000"
        response["Access-Control-Allow-Headers"] = (
            "Authorization, Content-Type, Cache-Control"
        )
        response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response["Access-Control-Allow-Credentials"] = "true"
        return response

    # POST请求需要认证
    if not request.user.is_authenticated:
        return Response(
            {"success": False, "message": "Authentication required"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    serializer = ImageAnalysisRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"success": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    image_id = serializer.validated_data["image_id"]

    try:
        # 获取上传的图片
        uploaded_image = UploadedImage.objects.get(id=image_id, user=request.user)

        # 获取图片路径
        image_path = uploaded_image.file_path.path

        # 更新图片状态
        uploaded_image.processing_status = "processing"
        uploaded_image.save()

        # 创建流式响应
        def event_stream():
            try:
                for chunk in analyze_food_image_streaming(image_path, image_id):
                    yield chunk

                # 分析完成，更新状态
                uploaded_image.processing_status = "completed"
                uploaded_image.save()

            except Exception as e:
                logger.error(f"Streaming analysis error: {str(e)}")
                uploaded_image.processing_status = "failed"
                uploaded_image.save()
                yield f"data: {json.dumps({'step': 'error', 'error': str(e)})}\n\n"

        def byte_stream():
            for chunk in event_stream():
                yield chunk.encode("utf-8")

        response = StreamingHttpResponse(
            byte_stream(), content_type="text/event-stream; charset=utf-8"
        )
        # SSE 标准头部
        response["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response["Pragma"] = "no-cache"
        response["Expires"] = "0"

        # CORS 头部
        response["Access-Control-Allow-Origin"] = "http://localhost:3000"
        response["Access-Control-Allow-Headers"] = (
            "Authorization, Content-Type, Cache-Control"
        )
        response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response["Access-Control-Allow-Credentials"] = "true"

        # 禁用代理缓冲（对于生产环境）
        response["X-Accel-Buffering"] = "no"  # nginx
        response["X-Sendfile-Type"] = "X-Accel-Redirect"  # apache

        return response

    except UploadedImage.DoesNotExist:
        return Response(
            {"success": False, "message": "Image not found"},
            status=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        logger.error(f"Streaming analysis setup failed: {str(e)}")
        return Response(
            {"success": False, "message": f"Analysis setup failed: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def analyze_image(request):
    """Analyze an uploaded image for food recognition"""

    serializer = ImageAnalysisRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"success": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    image_id = serializer.validated_data["image_id"]

    try:
        # 获取上传的图片
        uploaded_image = UploadedImage.objects.get(id=image_id, user=request.user)

        # 获取图片路径
        image_path = uploaded_image.file_path.path

        # 使用新的两段式分析
        analysis_result = analyze_food_image_two_stage(image_path)

        # 更新图片状态
        uploaded_image.processing_status = "completed"
        uploaded_image.save()

        if analysis_result["success"]:
            return Response(
                {
                    "success": True,
                    "data": {
                        "analysis_id": image_id,
                        "status": "completed",
                        "food_analysis": analysis_result,
                        # 保持向后兼容性，提供关键词列表
                        "keywords": [
                            food["name"]
                            for food in analysis_result["stage_1"]["food_types"]
                        ],
                    },
                    "message": "Two-stage image analysis completed",
                }
            )
        else:
            return Response(
                {
                    "success": False,
                    "data": {
                        "analysis_id": image_id,
                        "status": "failed",
                        "error": analysis_result.get("error", "Analysis failed"),
                        "food_analysis": analysis_result,
                    },
                    "message": "Image analysis failed",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    except UploadedImage.DoesNotExist:
        return Response(
            {"success": False, "message": "Image not found"},
            status=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        logger.error(f"Image analysis failed: {str(e)}")
        return Response(
            {"success": False, "message": f"Image analysis failed: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_image_results(request, image_id):
    """Get analysis results for an image"""

    try:
        service = FoodImageAnalysisService()
        result = service.get_image_analysis_results(image_id, request.user.id)

        if result["success"]:
            return Response({"success": True, "data": result})
        else:
            return Response(
                {"success": False, "message": result.get("error", "Results not found")},
                status=status.HTTP_404_NOT_FOUND,
            )

    except Exception as e:
        logger.error(f"Failed to get image results: {str(e)}")
        return Response(
            {"success": False, "message": f"Failed to get results: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def confirm_food_recognition(request):
    """Confirm or reject a food recognition result"""

    serializer = ConfirmFoodRecognitionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"success": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    result_id = serializer.validated_data["result_id"]
    is_confirmed = serializer.validated_data["is_confirmed"]

    try:
        service = FoodImageAnalysisService()
        result = service.confirm_food_recognition(
            result_id, request.user.id, is_confirmed
        )

        if result["success"]:
            return Response(
                {
                    "success": True,
                    "data": result,
                    "message": "Food recognition updated successfully",
                }
            )
        else:
            return Response(
                {
                    "success": False,
                    "message": result.get("error", "Failed to update recognition"),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    except Exception as e:
        logger.error(f"Failed to confirm recognition: {str(e)}")
        return Response(
            {"success": False, "message": f"Failed to confirm recognition: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_meal_from_image(request):
    """Create a meal from confirmed food recognition results"""

    serializer = CreateMealFromImageSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"success": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    image_id = serializer.validated_data["image_id"]
    meal_type = serializer.validated_data["meal_type"]
    date = serializer.validated_data.get("date")

    try:
        service = FoodImageAnalysisService()
        result = service.create_meal_from_image(
            image_id,
            request.user.id,
            meal_type,
            date.strftime("%Y-%m-%d") if date else None,
        )

        if result["success"]:
            return Response(
                {
                    "success": True,
                    "data": result,
                    "message": "Meal created successfully",
                },
                status=status.HTTP_201_CREATED,
            )
        else:
            return Response(
                {
                    "success": False,
                    "message": result.get("error", "Failed to create meal"),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    except Exception as e:
        logger.error(f"Failed to create meal from image: {str(e)}")
        return Response(
            {"success": False, "message": f"Failed to create meal: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_user_images(request):
    """Get user's uploaded images"""

    try:
        images = UploadedImage.objects.filter(user=request.user).order_by(
            "-uploaded_at"
        )

        # Pagination
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 20))

        start = (page - 1) * page_size
        end = start + page_size

        paginated_images = images[start:end]

        serializer = UploadedImageSerializer(paginated_images, many=True)

        return Response(
            {
                "success": True,
                "data": {
                    "images": serializer.data,
                    "pagination": {
                        "page": page,
                        "page_size": page_size,
                        "total_count": images.count(),
                        "has_next": end < images.count(),
                        "has_previous": page > 1,
                    },
                },
            }
        )

    except Exception as e:
        logger.error(f"Failed to get user images: {str(e)}")
        return Response(
            {"success": False, "message": f"Failed to get images: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_image(request, image_id):
    """Delete an uploaded image"""

    try:
        image = UploadedImage.objects.get(id=image_id, user=request.user)
        image.delete()

        return Response({"success": True, "message": "Image deleted successfully"})

    except UploadedImage.DoesNotExist:
        return Response(
            {"success": False, "message": "Image not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    except Exception as e:
        logger.error(f"Failed to delete image: {str(e)}")
        return Response(
            {"success": False, "message": f"Failed to delete image: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def detect_barcodes(request):
    """Detect barcodes in an uploaded image"""

    serializer = BarcodeDetectionRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"success": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    image_id = serializer.validated_data["image_id"]

    try:
        # Get uploaded image
        uploaded_image = UploadedImage.objects.get(id=image_id, user=request.user)
        image_path = uploaded_image.file_path.path

        # Initialize barcode detection service
        barcode_service = BarcodeDetectionService()

        # Check if dependencies are available
        if not barcode_service.dependencies_available:
            return Response(
                {
                    "success": False,
                    "message": "Barcode detection dependencies are not installed. Please install libzbar0 and libzbar-dev system packages.",
                    "data": {
                        "image_id": image_id,
                        "total_barcodes": 0,
                        "food_barcodes": 0,
                        "barcodes": [],
                        "food_barcodes_only": [],
                    },
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # Detect barcodes
        detected_barcodes = barcode_service.detect_barcodes_from_path(image_path)

        # Filter for food-related barcodes
        food_barcodes = [
            barcode
            for barcode in detected_barcodes
            if barcode.get("is_food_barcode", False)
        ]

        logger.info(
            f"Detected {len(detected_barcodes)} total barcodes, {len(food_barcodes)} food barcodes"
        )

        return Response(
            {
                "success": True,
                "data": {
                    "image_id": image_id,
                    "total_barcodes": len(detected_barcodes),
                    "food_barcodes": len(food_barcodes),
                    "barcodes": detected_barcodes,
                    "food_barcodes_only": food_barcodes,
                },
                "message": f"Found {len(detected_barcodes)} barcodes ({len(food_barcodes)} food-related)",
            }
        )

    except UploadedImage.DoesNotExist:
        return Response(
            {"success": False, "message": "Image not found"},
            status=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        logger.error(f"Barcode detection failed: {str(e)}")
        return Response(
            {"success": False, "message": f"Barcode detection failed: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def search_usda_by_barcode(request):
    """Search USDA FoodData Central by barcode"""

    serializer = USDABarcodeSearchSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"success": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    barcode = serializer.validated_data["barcode"]

    try:
        # Initialize food data service
        food_service = FoodDataService()

        # Search USDA by barcode
        usda_results = food_service.search_usda_by_barcode(barcode)

        if usda_results["success"]:
            return Response(
                {
                    "success": True,
                    "data": {
                        "barcode": barcode,
                        "usda_results": usda_results["foods"],
                        "total_results": usda_results["total_results"],
                    },
                    "message": f"Found {usda_results['total_results']} USDA products for barcode {barcode}",
                }
            )
        else:
            return Response(
                {
                    "success": False,
                    "data": {
                        "barcode": barcode,
                        "usda_results": [],
                        "total_results": 0,
                    },
                    "message": usda_results.get("message", "No USDA products found"),
                }
            )

    except Exception as e:
        logger.error(f"USDA barcode search failed: {str(e)}")
        return Response(
            {"success": False, "message": f"USDA search failed: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def analyze_image_with_barcode(request):
    """Combined image analysis: food recognition + barcode detection"""

    serializer = ImageAnalysisRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"success": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    image_id = serializer.validated_data["image_id"]

    try:
        # Get uploaded image
        uploaded_image = UploadedImage.objects.get(id=image_id, user=request.user)
        image_path = uploaded_image.file_path.path

        # Initialize services
        barcode_service = BarcodeDetectionService()
        food_service = FoodDataService()

        # Check if barcode dependencies are available
        if not barcode_service.dependencies_available:
            logger.warning(
                "Barcode detection dependencies not available, skipping barcode detection"
            )
            detected_barcodes = []
            food_barcodes = []
        else:
            # 1. Detect barcodes
            detected_barcodes = barcode_service.detect_barcodes_from_path(image_path)
            food_barcodes = [
                barcode
                for barcode in detected_barcodes
                if barcode.get("is_food_barcode", False)
            ]

        # 2. Search USDA and Open Food Facts for detected food barcodes
        usda_barcode_results = []
        openfoodfacts_results = []

        for barcode in food_barcodes:
            barcode_data = barcode.get("data", "")

            # Use combined search for both USDA and Open Food Facts
            combined_result = food_service.search_barcode_combined(barcode_data)

            if combined_result.get("success") and combined_result.get("data"):
                data = combined_result["data"]

                # Add USDA results
                if data.get("usda_results"):
                    usda_barcode_results.extend(
                        [
                            {
                                **food,
                                "source_barcode": barcode_data,
                                "barcode_info": barcode,
                            }
                            for food in data["usda_results"]
                        ]
                    )

                # Add Open Food Facts result
                if data.get("openfoodfacts_result"):
                    openfoodfacts_results.append(
                        {
                            **data["openfoodfacts_result"],
                            "source_barcode": barcode_data,
                            "barcode_info": barcode,
                        }
                    )

        # 3. Run traditional food analysis
        food_analysis = analyze_food_image_two_stage(image_path)

        # Update image status
        uploaded_image.processing_status = "completed"
        uploaded_image.save()

        return Response(
            {
                "success": True,
                "data": {
                    "image_id": image_id,
                    "status": "completed",
                    "barcode_detection": {
                        "total_barcodes": len(detected_barcodes),
                        "food_barcodes": len(food_barcodes),
                        "barcodes": detected_barcodes,
                    },
                    "usda_barcode_results": {
                        "total_products": len(usda_barcode_results),
                        "products": usda_barcode_results,
                    },
                    "openfoodfacts_results": {
                        "total_products": len(openfoodfacts_results),
                        "products": openfoodfacts_results,
                    },
                    "food_analysis": food_analysis,
                },
                "message": f"Analysis complete: {len(food_barcodes)} barcodes, {len(usda_barcode_results)} USDA + {len(openfoodfacts_results)} Open Food Facts products found",
            }
        )

    except UploadedImage.DoesNotExist:
        return Response(
            {"success": False, "message": "Image not found"},
            status=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        logger.error(f"Combined image analysis failed: {str(e)}")
        return Response(
            {"success": False, "message": f"Analysis failed: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def search_openfoodfacts_by_barcode(request):
    """Search Open Food Facts database by barcode"""

    serializer = USDABarcodeSearchSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"success": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    barcode = serializer.validated_data["barcode"]

    try:
        # Initialize food data service
        food_service = FoodDataService()

        # Search Open Food Facts by barcode
        off_result = food_service.search_openfoodfacts_by_barcode(barcode)

        if off_result["success"]:
            return Response(
                {
                    "success": True,
                    "data": {
                        "barcode": barcode,
                        "product": off_result["product"],
                    },
                    "message": off_result["message"],
                }
            )
        else:
            return Response(
                {
                    "success": False,
                    "data": {
                        "barcode": barcode,
                        "product": None,
                    },
                    "message": off_result.get(
                        "message", "No product found in Open Food Facts"
                    ),
                }
            )

    except Exception as e:
        logger.error(f"Open Food Facts barcode search failed: {str(e)}")
        return Response(
            {"success": False, "message": f"Open Food Facts search failed: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def search_barcode_combined(request):
    """Search barcode in both USDA and Open Food Facts databases"""

    serializer = USDABarcodeSearchSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"success": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    barcode = serializer.validated_data["barcode"]

    try:
        # Initialize food data service
        food_service = FoodDataService()

        # Search both databases
        combined_result = food_service.search_barcode_combined(barcode)

        if combined_result["success"]:
            return Response(
                {
                    "success": True,
                    "data": combined_result["data"],
                    "message": combined_result["message"],
                }
            )
        else:
            return Response(
                {
                    "success": False,
                    "message": combined_result.get("message", "No products found"),
                }
            )

    except Exception as e:
        logger.error(f"Combined barcode search failed: {str(e)}")
        return Response(
            {"success": False, "message": f"Combined search failed: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_user_foods_from_recognition(request):
    """
    Create user foods from image recognition results

    POST data:
    - nutrition_data: List of nutrition data dictionaries from recognition
    """
    try:
        nutrition_data_list = request.data.get("nutrition_data", [])

        if not nutrition_data_list:
            return Response(
                {"success": False, "message": "No nutrition data provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created_foods = []
        updated_foods = []
        errors = []

        for nutrition_data in nutrition_data_list:
            result = create_user_food_from_recognition(request.user.id, nutrition_data)

            if result["success"]:
                if result["is_new"]:
                    created_foods.append(result["food_data"])
                else:
                    updated_foods.append(result["food_data"])
            else:
                errors.append(
                    {
                        "food_name": nutrition_data.get("food_name", "Unknown"),
                        "error": result.get("error", "Unknown error"),
                    }
                )

        # Log the activity
        logger.info(
            f"User {request.user.id} created/updated foods from recognition: "
            f"{len(created_foods)} new, {len(updated_foods)} updated, {len(errors)} errors"
        )

        return Response(
            {
                "success": True,
                "created_foods": created_foods,
                "updated_foods": updated_foods,
                "errors": errors,
                "summary": {
                    "total_processed": len(nutrition_data_list),
                    "created_count": len(created_foods),
                    "updated_count": len(updated_foods),
                    "error_count": len(errors),
                },
                "message": f"Processed {len(nutrition_data_list)} foods: "
                f"{len(created_foods)} created, {len(updated_foods)} updated",
            },
            status=status.HTTP_201_CREATED,
        )

    except Exception as e:
        logger.error(f"Error in create_user_foods_from_recognition: {str(e)}")
        return Response(
            {"success": False, "message": f"Server error: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def create_food_from_barcode(request):
    """
    Create a Food object from barcode scan

    POST data:
    - barcode: Product barcode/UPC code
    """
    try:
        serializer = USDABarcodeSearchSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        barcode = serializer.validated_data["barcode"]

        # Import here to avoid circular imports
        from foods.services import FoodDataService

        food_service = FoodDataService()
        result = food_service.create_food_from_barcode(barcode, request.user.id)

        if result.get("success"):
            return Response(
                {"success": True, "food": result["food"], "message": result["message"]},
                status=status.HTTP_201_CREATED,
            )
        else:
            return Response(
                {
                    "success": False,
                    "message": result.get(
                        "message", "Failed to create food from barcode"
                    ),
                },
                status=status.HTTP_404_NOT_FOUND,
            )

    except Exception as e:
        logger.error(f"Error creating food from barcode: {str(e)}")
        return Response(
            {"success": False, "error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
