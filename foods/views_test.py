"""
Minimal test views for debugging
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


@api_view(["GET"])
def test_search_foods(request):
    """Test search endpoint - no auth required"""
    return Response(
        {
            "success": True,
            "message": "Test endpoint working",
            "data": {
                "foods": [],
                "total_count": 0,
                "search_term": request.GET.get("search", ""),
            },
        }
    )
