#!/usr/bin/env python
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'spart.settings')
django.setup()

from agent_ai.models import Resposta, Manual
from agent_ai.embedding import gerar_embeddings

def corrigir_embeddings():
    print("=== CORREÇÃO DOS EMBEDDINGS ===")
    
    respostas = Resposta.objects.all()
    total = respostas.count()
    
    print(f"Total de respostas para corrigir: {total}")
    
    for i, resposta in enumerate(respostas, 1):
        print(f"\nProcessando resposta {i}/{total} (ID: {resposta.id})")
        print(f"Manual: {resposta.manual.title}")
        
        try:
            # Verificar embedding atual
            embedding_atual = resposta.get_embedding()
            print(f"Embedding atual: {len(embedding_atual)} dimensões")
            
            # Gerar novo embedding com o modelo correto
            print("Gerando novo embedding...")
            novo_embedding = gerar_embeddings(resposta.content)
            print(f"Novo embedding: {len(novo_embedding)} dimensões")
            
            # Salvar novo embedding
            resposta.set_embedding(novo_embedding)
            resposta.save()
            
            print("✓ Embedding atualizado com sucesso")
            
        except Exception as e:
            print(f"✗ Erro ao processar resposta {resposta.id}: {e}")
    
    print("\n=== TESTE APÓS CORREÇÃO ===")
    pergunta_teste = "backup"
    print(f"Testando busca para: '{pergunta_teste}'")
    
    try:
        pergunta_embedding = gerar_embeddings(pergunta_teste)
        respostas_encontradas, similaridades = Resposta.objects.buscar_por_similaridade(
            pergunta_embedding, limite_similaridade=0.1, top_k=5
        )
        
        print(f"Encontradas {len(respostas_encontradas)} respostas relevantes:")
        for i, (resp, sim) in enumerate(zip(respostas_encontradas, similaridades), 1):
            print(f"  {i}. Similaridade: {sim:.4f} - Manual: {resp.manual.title}")
            
    except Exception as e:
        print(f"Erro no teste: {e}")

if __name__ == "__main__":
    corrigir_embeddings()