import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'spart.settings')
django.setup()

from agent_ai.models import ManualProcessado, ImagemManual

print(f'Manuais processados: {ManualProcessado.objects.count()}')
print(f'Imagens de manuais: {ImagemManual.objects.count()}')

print('\nÚltimos manuais processados:')
for mp in ManualProcessado.objects.all()[:5]:
    print(f'- {mp.titulo} ({mp.total_imagens} imagens)')
    print(f'  Embedding: {"Sim" if mp.embedding else "Não"}')
    print(f'  Criado em: {mp.created_at}')
    print()

print('\nPrimeiras imagens:')
for img in ImagemManual.objects.all()[:5]:
    print(f'- {img.nome_arquivo} (Manual: {img.manual_processado.titulo})')
    print(f'  URL original: {img.url_original}')
    print(f'  Tamanho: {img.tamanho_bytes} bytes')
    print()