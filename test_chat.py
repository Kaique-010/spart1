import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'spart.settings')
django.setup()

from agent_ai.views import buscar_contexto_relevante

try:
    contexto, similaridade = buscar_contexto_relevante('Como funciona o controle de grade?')
    print('Contexto encontrado:', bool(contexto))
    print('Similaridade:', similaridade)
    print('Tipo do contexto:', type(contexto))
    
    if contexto and hasattr(contexto, 'imagens'):
        print('Imagens:', contexto.imagens.count())
        if contexto.imagens.count() > 0:
            primeira_imagem = contexto.imagens.first()
            print('Primeira imagem URL:', primeira_imagem.get_url_servida())
            print('Primeira imagem alt_text:', primeira_imagem.alt_text)
except Exception as e:
    print('Erro:', str(e))
    import traceback
    traceback.print_exc()