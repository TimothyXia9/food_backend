from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserProfile, UserActivityLog


@admin.register(User)
class UserAdmin(BaseUserAdmin):
	"""自定义用户管理界面"""
	list_display = ('username', 'email', 'nickname', 'is_staff', 'is_active', 'date_joined')
	list_filter = ('is_staff', 'is_active', 'date_joined')
	search_fields = ('username', 'email', 'nickname')
	ordering = ('-date_joined',)
	
	fieldsets = BaseUserAdmin.fieldsets + (
		('额外信息', {'fields': ('nickname',)}),
	)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
	"""用户档案管理界面"""
	list_display = ('user', 'gender', 'height', 'weight', 'daily_calorie_goal', 'created_at')
	list_filter = ('gender', 'created_at')
	search_fields = ('user__username', 'user__email')
	readonly_fields = ('created_at', 'updated_at')
	
	fieldsets = (
		('用户信息', {
			'fields': ('user',)
		}),
		('身体信息', {
			'fields': ('date_of_birth', 'gender', 'height', 'weight')
		}),
		('目标设置', {
			'fields': ('daily_calorie_goal',)
		}),
		('时间戳', {
			'fields': ('created_at', 'updated_at'),
			'classes': ('collapse',)
		}),
	)


@admin.register(UserActivityLog)
class UserActivityLogAdmin(admin.ModelAdmin):
	"""用户活动日志管理界面"""
	list_display = ('user', 'activity_type', 'ip_address', 'created_at')
	list_filter = ('activity_type', 'created_at')
	search_fields = ('user__username', 'activity_type', 'ip_address')
	readonly_fields = ('created_at',)
	date_hierarchy = 'created_at'
	
	fieldsets = (
		('基本信息', {
			'fields': ('user', 'activity_type', 'created_at')
		}),
		('详细信息', {
			'fields': ('activity_data', 'ip_address', 'user_agent'),
			'classes': ('collapse',)
		}),
	)
	
	def has_add_permission(self, request):
		"""禁止手动添加活动日志"""
		return False