# agent_ai/apps.py

from django.apps import AppConfig

class AgentAiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'agent_ai'

    def ready(self):
        import agent_ai.signals
