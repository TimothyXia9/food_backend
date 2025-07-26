from django.contrib import admin
from .models import Food, FoodAlias, FoodSearchLog


@admin.register(Food)
class FoodAdmin(admin.ModelAdmin):
    """食物管理界面"""

    list_display = (
        "name",
        "brand",
        "calories_per_100g",
        "is_verified",
        "created_by",
        "created_at",
    )
    list_filter = ("is_verified", "created_at", "created_by")
    search_fields = ("name", "brand", "barcode", "usda_fdc_id")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"

    fieldsets = (
        (
            "基本信息",
            {"fields": ("name", "brand", "barcode", "serving_size", "usda_fdc_id")},
        ),
        (
            "营养信息 (每100g)",
            {
                "fields": (
                    "calories_per_100g",
                    "protein_per_100g",
                    "fat_per_100g",
                    "carbs_per_100g",
                    "fiber_per_100g",
                    "sugar_per_100g",
                    "sodium_per_100g",
                )
            },
        ),
        ("验证信息", {"fields": ("is_verified", "created_by")}),
        ("时间戳", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def get_queryset(self, request):
        """优化查询性能"""
        return super().get_queryset(request).select_related("created_by")


@admin.register(FoodAlias)
class FoodAliasAdmin(admin.ModelAdmin):
    """食物别名管理界面"""

    list_display = ("alias", "food", "created_at")
    search_fields = ("alias", "food__name")
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"

    def get_queryset(self, request):
        """优化查询性能"""
        return super().get_queryset(request).select_related("food")


@admin.register(FoodSearchLog)
class FoodSearchLogAdmin(admin.ModelAdmin):
    """食物搜索日志管理界面"""

    list_display = (
        "search_query",
        "user",
        "search_type",
        "results_count",
        "created_at",
    )
    list_filter = ("search_type", "created_at")
    search_fields = ("search_query", "user__username")
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"

    def get_queryset(self, request):
        """优化查询性能"""
        return super().get_queryset(request).select_related("user")

    def has_add_permission(self, request):
        """禁止手动添加搜索日志"""
        return False
