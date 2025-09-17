from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    def ready(self):
        import core.signals  # noqa
        # Demo-specific guards (safe to import always)
        try:
            import core.demo_signals  # noqa: F401
        except Exception:
            # Be tolerant if optional demo guards fail to import
            pass
