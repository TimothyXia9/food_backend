from django.apps import AppConfig
import logging

logger = logging.getLogger("startup")


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"

    def ready(self):
        logger.info(f"[STARTUP] {self.name} app is ready")
        try:
            from django.contrib.auth import get_user_model

            User = get_user_model()
            logger.info(f"[STARTUP] User model loaded: {User}")
        except Exception as e:
            logger.error(f"[STARTUP] Error loading user model: {e}")
