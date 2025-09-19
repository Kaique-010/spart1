from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import ManualViewSet, RespostaViewSet, AgenteAIViewSet

# Router para as ViewSets
router = DefaultRouter()
router.register(r'manuais', ManualViewSet, basename='manual')
router.register(r'respostas', RespostaViewSet, basename='resposta')
router.register(r'agente', AgenteAIViewSet, basename='agente')

# URLs da API
api_urlpatterns = [
    path('', include(router.urls)),
]

# URLs específicas para compatibilidade com sistema existente
compat_urlpatterns = [
    # Mantém endpoints existentes para compatibilidade
    path('perguntar/', AgenteAIViewSet.as_view({'post': 'perguntar'}), name='api_perguntar'),
    path('perguntar/stream/', AgenteAIViewSet.as_view({'post': 'perguntar_stream'}), name='api_perguntar_stream'),
]

urlpatterns = api_urlpatterns + compat_urlpatterns