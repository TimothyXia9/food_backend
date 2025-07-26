from django.contrib import admin
from .models import Meal, MealFood, DailySummary


@admin.register(Meal)
class MealAdmin(admin.ModelAdmin):
    """餐食管理界面"""

    list_display = (
        "id",
        "user",
        "date",
        "meal_type",
        "name",
        "get_total_calories",
        "get_food_count",
        "created_at",
    )
    list_filter = ("meal_type", "created_at")
    search_fields = ("user__username", "name", "notes", "id")
    readonly_fields = (
        "created_at",
        "updated_at",
        "get_total_calories",
        "get_total_protein",
        "get_total_fat",
        "get_total_carbs",
    )
    date_hierarchy = "created_at"

    # 启用删除功能用于调试
    actions = ["delete_selected", "delete_with_foods"]
    list_per_page = 20

    fieldsets = (
        ("基本信息", {"fields": ("user", "date", "meal_type", "name")}),
        ("详细信息", {"fields": ("notes",)}),
        (
            "营养统计",
            {
                "fields": (
                    "get_total_calories",
                    "get_total_protein",
                    "get_total_fat",
                    "get_total_carbs",
                ),
                "classes": ("collapse",),
            },
        ),
        ("时间戳", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def get_total_calories(self, obj):
        """显示总卡路里"""
        return f"{obj.total_calories:.1f} kcal"

    get_total_calories.short_description = "总卡路里"

    def get_total_protein(self, obj):
        """显示总蛋白质"""
        return f"{obj.total_protein:.1f}g"

    get_total_protein.short_description = "总蛋白质"

    def get_total_fat(self, obj):
        """显示总脂肪"""
        return f"{obj.total_fat:.1f}g"

    get_total_fat.short_description = "总脂肪"

    def get_total_carbs(self, obj):
        """显示总碳水化合物"""
        return f"{obj.total_carbs:.1f}g"

    get_total_carbs.short_description = "总碳水化合物"

    def get_food_count(self, obj):
        """显示食物数量"""
        return obj.meal_foods.count()

    get_food_count.short_description = "食物数量"

    def delete_with_foods(self, request, queryset):
        """删除餐食及其所有食物 - 调试用"""
        total_deleted = 0
        for meal in queryset:
            food_count = meal.meal_foods.count()
            meal_name = f"{meal.name} ({meal.date})"
            meal.delete()  # 会级联删除相关的MealFood记录
            total_deleted += 1
            self.message_user(
                request, f"已删除餐食: {meal_name}, 包含 {food_count} 个食物"
            )

        self.message_user(request, f"总共删除了 {total_deleted} 个餐食")

    delete_with_foods.short_description = "删除选中的餐食及其食物 (调试用)"

    def get_queryset(self, request):
        """优化查询性能"""
        return (
            super()
            .get_queryset(request)
            .select_related("user")
            .prefetch_related("meal_foods")
        )


@admin.register(MealFood)
class MealFoodAdmin(admin.ModelAdmin):
    """餐食食物管理界面"""

    list_display = ("meal", "food", "quantity", "get_calories", "added_at")
    list_filter = ("added_at", "meal__meal_type")
    search_fields = ("meal__user__username", "food__name", "meal__name")
    readonly_fields = ("calories", "protein", "fat", "carbs", "added_at")

    fieldsets = (
        ("基本信息", {"fields": ("meal", "food", "quantity")}),
        (
            "营养信息 (自动计算)",
            {
                "fields": ("calories", "protein", "fat", "carbs"),
                "classes": ("collapse",),
            },
        ),
        ("时间戳", {"fields": ("added_at",), "classes": ("collapse",)}),
    )

    def get_calories(self, obj):
        """显示卡路里"""
        return f"{obj.calories:.1f} kcal"

    get_calories.short_description = "卡路里"

    def get_queryset(self, request):
        """优化查询性能"""
        return (
            super().get_queryset(request).select_related("meal", "food", "meal__user")
        )


@admin.register(DailySummary)
class DailySummaryAdmin(admin.ModelAdmin):
    """每日汇总管理界面"""

    list_display = (
        "user",
        "date",
        "get_total_calories",
        "get_total_protein",
        "get_total_fat",
        "get_total_carbs",
        "weight_recorded",
    )
    list_filter = ("date", "created_at")
    search_fields = ("user__username",)
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "date"

    fieldsets = (
        ("基本信息", {"fields": ("user", "date")}),
        (
            "营养汇总",
            {
                "fields": (
                    "total_calories",
                    "total_protein",
                    "total_fat",
                    "total_carbs",
                    "total_fiber",
                )
            },
        ),
        ("体重记录", {"fields": ("weight_recorded",)}),
        ("时间戳", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def get_total_calories(self, obj):
        """显示总卡路里"""
        return f"{obj.total_calories:.1f} kcal"

    get_total_calories.short_description = "总卡路里"

    def get_total_protein(self, obj):
        """显示总蛋白质"""
        return f"{obj.total_protein:.1f}g"

    get_total_protein.short_description = "总蛋白质"

    def get_total_fat(self, obj):
        """显示总脂肪"""
        return f"{obj.total_fat:.1f}g"

    get_total_fat.short_description = "总脂肪"

    def get_total_carbs(self, obj):
        """显示总碳水化合物"""
        return f"{obj.total_carbs:.1f}g"

    get_total_carbs.short_description = "总碳水化合物"

    def get_queryset(self, request):
        """优化查询性能"""
        return super().get_queryset(request).select_related("user")

    actions = ["update_from_meals"]

    def update_from_meals(self, request, queryset):
        """从餐食更新汇总数据"""
        updated_count = 0
        for summary in queryset:
            summary.update_from_meals()
            updated_count += 1

        self.message_user(request, f"已更新 {updated_count} 条每日汇总记录")

    update_from_meals.short_description = "从餐食更新汇总数据"
