#!/usr/bin/env python
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'spart.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from agent_ai.models import Resposta, Manual
from agent_ai.embedding import gerar_embeddings
import json

def limpar_embeddings_corrompidos():
    """Remove embeddings corrompidos do banco de dados."""
    print("🔍 Verificando embeddings corrompidos...")
    
    respostas = Resposta.objects.all()
    corrompidos = 0
    
    for resposta in respostas:
        try:
            if resposta.embedding:
                # Tenta decodificar o embedding
                embedding_data = json.loads(resposta.embedding)
                if not isinstance(embedding_data, list) or len(embedding_data) == 0:
                    raise ValueError("Embedding inválido")
        except (json.JSONDecodeError, ValueError, UnicodeDecodeError) as e:
            print(f"❌ Embedding corrompido encontrado (ID: {resposta.id}): {str(e)[:50]}...")
            resposta.embedding = None
            resposta.save()
            corrompidos += 1
    
    print(f"🧹 {corrompidos} embeddings corrompidos removidos.")
    return corrompidos

def recriar_embeddings():
    """Recria embeddings para respostas sem embedding."""
    print("🔄 Recriando embeddings...")
    
    respostas_sem_embedding = Resposta.objects.filter(embedding__isnull=True)
    total = respostas_sem_embedding.count()
    
    if total == 0:
        print("✅ Todas as respostas já possuem embeddings válidos.")
        return
    
    print(f"📝 Encontradas {total} respostas sem embedding.")
    
    for i, resposta in enumerate(respostas_sem_embedding, 1):
        try:
            print(f"⏳ Processando {i}/{total}: {resposta.content[:50]}...")
            embedding_data = gerar_embeddings(resposta.content)
            resposta.set_embedding(embedding_data)
            resposta.save()
            print(f"✅ Embedding criado com sucesso (ID: {resposta.id})")
        except Exception as e:
            print(f"❌ Erro ao criar embedding (ID: {resposta.id}): {e}")
    
    print(f"🎉 Processo concluído!")

def verificar_integridade():
    """Verifica a integridade dos embeddings após a correção."""
    print("\n🔍 Verificando integridade dos embeddings...")
    
    respostas = Resposta.objects.all()
    validos = 0
    invalidos = 0
    
    for resposta in respostas:
        try:
            embedding = resposta.get_embedding()
            if embedding and isinstance(embedding, list) and len(embedding) > 0:
                validos += 1
            else:
                invalidos += 1
        except Exception:
            invalidos += 1
    
    print(f"✅ Embeddings válidos: {validos}")
    print(f"❌ Embeddings inválidos: {invalidos}")
    print(f"📊 Total de respostas: {respostas.count()}")
    
    return validos, invalidos

def main():
    print("🚀 Iniciando correção do banco de dados...")
    print("=" * 50)
    
    # Passo 1: Limpar embeddings corrompidos
    corrompidos = limpar_embeddings_corrompidos()
    
    # Passo 2: Recriar embeddings
    recriar_embeddings()
    
    # Passo 3: Verificar integridade
    validos, invalidos = verificar_integridade()
    
    print("\n" + "=" * 50)
    print("📋 RESUMO DA CORREÇÃO")
    print("=" * 50)
    print(f"🧹 Embeddings corrompidos removidos: {corrompidos}")
    print(f"✅ Embeddings válidos: {validos}")
    print(f"❌ Embeddings inválidos: {invalidos}")
    
    if invalidos == 0:
        print("🎉 Banco de dados corrigido com sucesso!")
    else:
        print("⚠️  Ainda existem problemas no banco de dados.")

if __name__ == "__main__":
    main()