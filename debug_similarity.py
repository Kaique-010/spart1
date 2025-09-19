#!/usr/bin/env python
import os
import sys
import django
import numpy as np

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'spart.settings')
django.setup()

from agent_ai.models import Resposta, Manual
from agent_ai.embedding import gerar_embeddings

def debug_similaridade():
    print("=== DEBUG DETALHADO DA SIMILARIDADE ===")
    
    # Teste com pergunta simples
    pergunta = "backup"
    print(f"Pergunta de teste: '{pergunta}'")
    
    try:
        pergunta_embedding = gerar_embeddings(pergunta)
        pergunta_array = np.array(pergunta_embedding)
        pergunta_norm = pergunta_array / np.linalg.norm(pergunta_array)
        
        print(f"Embedding da pergunta:")
        print(f"  - Dimensões: {len(pergunta_embedding)}")
        print(f"  - Norma original: {np.linalg.norm(pergunta_array):.6f}")
        print(f"  - Norma normalizada: {np.linalg.norm(pergunta_norm):.6f}")
        print(f"  - Primeiros 5 valores: {pergunta_embedding[:5]}")
        
        print("\n=== ANÁLISE DE CADA RESPOSTA ===")
        
        for i, resposta in enumerate(Resposta.objects.all(), 1):
            print(f"\nResposta {i} (ID: {resposta.id}):")
            print(f"  Manual: {resposta.manual.title}")
            print(f"  Conteúdo (primeiros 100 chars): {resposta.content[:100]}...")
            
            try:
                resposta_embedding = resposta.get_embedding()
                resposta_array = np.array(resposta_embedding)
                resposta_norm = resposta_array / np.linalg.norm(resposta_array)
                
                print(f"  Embedding da resposta:")
                print(f"    - Dimensões: {len(resposta_embedding)}")
                print(f"    - Norma original: {np.linalg.norm(resposta_array):.6f}")
                print(f"    - Norma normalizada: {np.linalg.norm(resposta_norm):.6f}")
                print(f"    - Primeiros 5 valores: {resposta_embedding[:5]}")
                
                # Calcular similaridade manualmente
                similaridade = np.dot(pergunta_norm, resposta_norm)
                print(f"    - Similaridade calculada: {similaridade:.6f}")
                
                # Testar diferentes limites
                limites = [0.1, 0.2, 0.3, 0.4, 0.5]
                for limite in limites:
                    passou = similaridade > limite
                    print(f"    - Limite {limite}: {'✓' if passou else '✗'}")
                
            except Exception as e:
                print(f"    - ERRO ao processar embedding: {e}")
        
        print("\n=== TESTE COM BUSCA OFICIAL ===")
        respostas, similaridades = Resposta.objects.buscar_por_similaridade(
            pergunta_embedding, limite_similaridade=0.1, top_k=10
        )
        
        print(f"Busca oficial encontrou {len(respostas)} respostas:")
        for i, (resp, sim) in enumerate(zip(respostas, similaridades), 1):
            print(f"  {i}. Similaridade: {sim:.6f} - Manual: {resp.manual.title}")
            
    except Exception as e:
        print(f"ERRO GERAL: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_similaridade()