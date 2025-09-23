from django.apps import AppConfig


class GolfgeniusConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'golfgenius'
    verbose_name = 'Golf Genius Integration'
    
    def ready(self):
        """
        Perform initialization when the app is ready
        """
        # Import any signal handlers or startup code here if needed
        pass
