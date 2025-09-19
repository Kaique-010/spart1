from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('manual/<int:manual_id>/buscar/', views.buscar_manual, name='buscar_manual'),
    path('manual/<int:manual_id>/resposta/<str:query>/', views.buscar_resposta, name='buscar_resposta'),
    path('', views.spartacus_view, name='spartacus'),
    path('api/perguntar/', views.perguntar_spart, name='perguntar_spart'),
    path('api/perguntar/stream/', views.perguntar_spart_stream, name='perguntar_spart_stream'),

]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)