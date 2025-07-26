from django.apps import AppConfig
import logging

logger = logging.getLogger("startup")


class ImagesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "images"

    def ready(self):
        logger.info(f"[STARTUP] {self.name} app is ready")
        try:
            from .models import UploadedImage, FoodRecognitionResult

            logger.info(
                f"[STARTUP] Image models loaded: UploadedImage={UploadedImage}, FoodRecognitionResult={FoodRecognitionResult}"
            )
        except Exception as e:
            logger.error(f"[STARTUP] Error loading image models: {e}")
