from django.apps import AppConfig
import logging

logger = logging.getLogger('startup')

class MealsConfig(AppConfig):
	default_auto_field = 'django.db.models.BigAutoField'
	name = 'meals'

	def ready(self):
		logger.info(f"[STARTUP] {self.name} app is ready")
		try:
			from .models import Meal, MealFood, DailySummary
			logger.info(f"[STARTUP] Meal models loaded: Meal={Meal}, MealFood={MealFood}, DailySummary={DailySummary}")
		except Exception as e:
			logger.error(f"[STARTUP] Error loading meal models: {e}")
