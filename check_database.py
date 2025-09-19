#!/usr/bin/env python
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'spart.settings')
django.setup()

from agent_ai.models import Resposta, Manual
from agent_ai.embedding import gerar_embeddings
import numpy as np

def verificar_banco():
    print("=== STATUS DO BANCO DE DADOS ===")
    print(f"Total de manuais: {Manual.objects.count()}")
    print(f"Total de respostas: {Resposta.objects.count()}")
    
    respostas_com_embedding = Resposta.objects.exclude(embedding__isnull=True).exclude(embedding__exact="")
    print(f"Respostas com embedding: {respostas_com_embedding.count()}")
    
    print("\n=== DETALHES DAS RESPOSTAS ===")
    for i, resposta in enumerate(Resposta.objects.all()[:5], 1):
        embedding_valido = bool(resposta.embedding and resposta.embedding != "null" and resposta.embedding != "")
        tamanho_conteudo = len(resposta.content) if resposta.content else 0
        
        print(f"Resposta {i} (ID: {resposta.id}):")
        print(f"  - Manual: {resposta.manual.title}")
        print(f"  - Embedding válido: {embedding_valido}")
        print(f"  - Tamanho do conteúdo: {tamanho_conteudo} caracteres")
        
        if embedding_valido:
            try:
                embedding_array = resposta.get_embedding()
                print(f"  - Dimensão do embedding: {len(embedding_array)}")
            except Exception as e:
                print(f"  - Erro ao carregar embedding: {e}")
        print()
    
    print("\n=== TESTE DE BUSCA VETORIAL ===")
    if respostas_com_embedding.exists():
        pergunta_teste = "Como fazer backup"
        print(f"Testando busca para: '{pergunta_teste}'")
        
        try:
            pergunta_embedding = gerar_embeddings(pergunta_teste)
            print(f"Embedding da pergunta gerado: {len(pergunta_embedding)} dimensões")
            
            respostas, similaridades = Resposta.objects.buscar_por_similaridade(
                pergunta_embedding, limite_similaridade=0.1, top_k=3
            )
            
            print(f"Encontradas {len(respostas)} respostas relevantes:")
            for i, (resp, sim) in enumerate(zip(respostas, similaridades), 1):
                print(f"  {i}. Similaridade: {sim:.4f} - Manual: {resp.manual.title}")
                
        except Exception as e:
            print(f"Erro na busca vetorial: {e}")
    else:
        print("Nenhuma resposta com embedding encontrada para teste.")

if __name__ == "__main__":
    verificar_banco()