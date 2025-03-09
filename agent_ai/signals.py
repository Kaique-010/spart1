# agent_ai/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Manual
from .views import buscar_manual

@receiver(post_save, sender=Manual)
def gerar_resposta_automaticamente(sender, instance, created, **kwargs):
    print(f"Signal recebido para o Manual com ID {instance.id}. Novo manual? {'Sim' if created else 'Não'}")
    
    # Se o manual foi criado, chama a função para buscar a URL e gerar a resposta
    if created:
        print(f"Manual {instance.title} criado. Chamando buscar_manual()...")
        buscar_manual(None, instance.id)
    else:
        print(f"Manual {instance.title} já existe. Nenhuma ação será tomada.")
