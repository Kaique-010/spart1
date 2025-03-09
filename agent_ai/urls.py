from django.urls import path
from . import views

urlpatterns = [
    path('manual/<int:manual_id>/buscar/', views.buscar_manual, name='buscar_manual'),
    path('manual/<int:manual_id>/resposta/<str:query>/', views.buscar_resposta, name='buscar_resposta'),
    path('', views.spartacus_view, name='spartacus'),
    path('api/perguntar/', views.perguntar_spart, name='perguntar_spart'), 

]
