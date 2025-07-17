from django.contrib import admin
from django.utils.html import format_html
from .models import UploadedImage, FoodRecognitionResult


@admin.register(UploadedImage)
class UploadedImageAdmin(admin.ModelAdmin):
	"""上传图片管理界面"""
	list_display = ('filename', 'user', 'processing_status', 'get_file_size', 'get_dimensions', 'uploaded_at')
	list_filter = ('processing_status', 'mime_type', 'uploaded_at')
	search_fields = ('filename', 'user__username')
	readonly_fields = ('filename', 'file_size', 'mime_type', 'width', 'height', 'uploaded_at', 'processed_at', 'get_image_preview')
	date_hierarchy = 'uploaded_at'
	
	fieldsets = (
		('基本信息', {
			'fields': ('user', 'meal', 'filename', 'processing_status')
		}),
		('图片信息', {
			'fields': ('get_image_preview', 'file_path', 'get_file_size', 'mime_type', 'get_dimensions')
		}),
		('时间戳', {
			'fields': ('uploaded_at', 'processed_at'),
			'classes': ('collapse',)
		}),
	)
	
	def get_file_size(self, obj):
		"""显示文件大小"""
		if obj.file_size < 1024:
			return f"{obj.file_size} B"
		elif obj.file_size < 1024 * 1024:
			return f"{obj.file_size / 1024:.1f} KB"
		else:
			return f"{obj.file_size / (1024 * 1024):.1f} MB"
	get_file_size.short_description = "文件大小"
	
	def get_dimensions(self, obj):
		"""显示图片尺寸"""
		if obj.width and obj.height:
			return f"{obj.width} × {obj.height}"
		return "未知"
	get_dimensions.short_description = "图片尺寸"
	
	def get_image_preview(self, obj):
		"""显示图片预览"""
		if obj.file_path:
			return format_html(
				'<img src="{}" style="max-width: 200px; max-height: 200px;" />',
				obj.file_path.url
			)
		return "无图片"
	get_image_preview.short_description = "图片预览"
	
	def get_queryset(self, request):
		"""优化查询性能"""
		return super().get_queryset(request).select_related('user', 'meal')


@admin.register(FoodRecognitionResult)
class FoodRecognitionResultAdmin(admin.ModelAdmin):
	"""食物识别结果管理界面"""
	list_display = ('image', 'food', 'get_confidence_score', 'get_estimated_quantity', 'is_confirmed', 'created_at')
	list_filter = ('is_confirmed', 'created_at')
	search_fields = ('image__filename', 'food__name', 'image__user__username')
	readonly_fields = ('created_at', 'get_confidence_percentage')
	date_hierarchy = 'created_at'
	
	fieldsets = (
		('基本信息', {
			'fields': ('image', 'food', 'is_confirmed')
		}),
		('识别结果', {
			'fields': ('confidence_score', 'get_confidence_percentage', 'estimated_quantity')
		}),
		('时间戳', {
			'fields': ('created_at',),
			'classes': ('collapse',)
		}),
	)
	
	def get_confidence_score(self, obj):
		"""显示置信度分数"""
		return f"{obj.confidence_score:.4f}"
	get_confidence_score.short_description = "置信度"
	
	def get_confidence_percentage(self, obj):
		"""显示置信度百分比"""
		return f"{obj.confidence_score * 100:.2f}%"
	get_confidence_percentage.short_description = "置信度百分比"
	
	def get_estimated_quantity(self, obj):
		"""显示估计重量"""
		if obj.estimated_quantity:
			return f"{obj.estimated_quantity}g"
		return "未估计"
	get_estimated_quantity.short_description = "估计重量"
	
	def get_queryset(self, request):
		"""优化查询性能"""
		return super().get_queryset(request).select_related('image', 'food', 'image__user')
	
	actions = ['mark_as_confirmed', 'mark_as_unconfirmed']
	
	def mark_as_confirmed(self, request, queryset):
		"""标记为已确认"""
		updated_count = queryset.update(is_confirmed=True)
		self.message_user(request, f"已确认 {updated_count} 条识别结果")
	mark_as_confirmed.short_description = "标记为已确认"
	
	def mark_as_unconfirmed(self, request, queryset):
		"""标记为未确认"""
		updated_count = queryset.update(is_confirmed=False)
		self.message_user(request, f"已取消确认 {updated_count} 条识别结果")
	mark_as_unconfirmed.short_description = "标记为未确认"