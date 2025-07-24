from django.apps import AppConfig
import logging

logger = logging.getLogger('startup')

class FoodsConfig(AppConfig):
	default_auto_field = 'django.db.models.BigAutoField'
	name = 'foods'

	def ready(self):
		logger.info(f"[STARTUP] {self.name} app is ready")
		try:
			from .models import Food, FoodAlias
			logger.info(f"[STARTUP] Food models loaded: Food={Food}, FoodAlias={FoodAlias}")
		except Exception as e:
			logger.error(f"[STARTUP] Error loading food models: {e}")
