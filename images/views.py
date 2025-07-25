"""
Image API views for food recognition
"""

import asyncio
import os
import json
from PIL import Image
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
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
)
from .services import FoodImageAnalysisService

logger = logging.getLogger(__name__)


def clean_json_response(content: str) -> str:
    """
    清理OpenAI响应中的JSON，移除可能的代码块标记
    """
    cleaned_content = content.strip()
    
    # 移除各种可能的代码块标记
    if cleaned_content.startswith('```json'):
        cleaned_content = cleaned_content[7:]
    elif cleaned_content.startswith('```'):
        cleaned_content = cleaned_content[3:]
    
    if cleaned_content.endswith('```'):
        cleaned_content = cleaned_content[:-3]
    
    return cleaned_content.strip()


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

        # 第一阶段：识别食物种类
        logger.info(f"Stage 1: Identifying food types in image: {image_path}")

        stage1_prompt = """请识别这张图片中的所有食物种类，以JSON格式返回结果。返回格式如下：
{
	"foods": [
		{"name": "苹果", "confidence": 0.95},
		{"name": "香蕉", "confidence": 0.88},
		{"name": "面包", "confidence": 0.92}
	]
}
只返回JSON，不要添加其他说明文字。confidence值表示识别的置信度(0-1之间)。"""

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
                if "foods" in stage1_data and isinstance(stage1_data["foods"], list):
                    stage1_result["food_types"] = stage1_data["foods"]
                else:
                    # 如果JSON格式不正确，尝试解析为简单列表
                    food_names = [
                        item.get("name", "未知食物")
                        for item in stage1_data.get("foods", [])
                    ]
                    stage1_result["food_types"] = [
                        {"name": name, "confidence": 0.8} for name in food_names[:5]
                    ]
            except json.JSONDecodeError:
                # 如果JSON解析失败，使用默认值
                logger.warning(f"Failed to parse Stage 1 JSON response: {content}")
                stage1_result["food_types"] = [
                    {"name": "未识别食物", "confidence": 0.5}
                ]
        else:
            logger.error(
                f"Stage 1 OpenAI API error: {response.status_code} - {response.text}"
            )
            stage1_result["food_types"] = [{"name": "未识别食物", "confidence": 0.5}]

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

        return {"success": True, "stage_1": stage1_result, "stage_2": stage2_result}

    except Exception as e:
        logger.error(f"Error in two-stage food analysis: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "stage_1": {"food_types": []},
            "stage_2": {"food_portions": []},
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

        stage1_prompt = """请识别这张图片中的所有食物种类，以JSON格式返回结果。返回格式如下：
{
	"foods": [
		{"name": "苹果", "confidence": 0.95},
		{"name": "香蕉", "confidence": 0.88},
		{"name": "面包", "confidence": 0.92}
	]
}
只返回JSON，不要添加其他说明文字。confidence值表示识别的置信度(0-1之间)。"""

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
                if "foods" in stage1_data and isinstance(stage1_data["foods"], list):
                    stage1_result["food_types"] = stage1_data["foods"]
                else:
                    # 如果JSON格式不正确，尝试解析为简单列表
                    food_names = [
                        item.get("name", "未知食物")
                        for item in stage1_data.get("foods", [])
                    ]
                    stage1_result["food_types"] = [
                        {"name": name, "confidence": 0.8} for name in food_names[:5]
                    ]
            except json.JSONDecodeError:
                # 如果JSON解析失败，使用默认值
                logger.warning(f"Failed to parse Stage 1 JSON response: {content}")
                stage1_result["food_types"] = [
                    {"name": "未识别食物", "confidence": 0.5}
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

        # 发送最终结果
        final_result = {
            "step": "complete",
            "success": True,
            "stage_1": stage1_result,
            "stage_2": stage2_result,
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
