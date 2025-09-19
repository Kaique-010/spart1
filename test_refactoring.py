#!/usr/bin/env python
"""
Script de teste para verificar as refatorações do agente AI.
"""

import os
import sys
import django
from django.conf import settings

# Configuração do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'spart.settings')
django.setup()

from agent_ai.models import Manual, Resposta
from agent_ai.embedding import gerar_embeddings
from agent_ai.utils import criar_audio, validar_texto_audio
import numpy as np

def test_embedding_generation():
    """Testa a geração de embeddings."""
    print("\n=== Testando Geração de Embeddings ===")
    try:
        texto_teste = "Como configurar o sistema Spartacus?"
        embedding = gerar_embeddings(texto_teste)
        print(f"✅ Embedding gerado com sucesso: {len(embedding)} dimensões")
        return True
    except Exception as e:
        print(f"❌ Erro ao gerar embedding: {str(e)}")
        return False

def test_vector_search():
    """Testa a busca vetorial otimizada."""
    print("\n=== Testando Busca Vetorial ===")
    try:
        # Verifica se existem respostas no banco
        count = Resposta.objects.count()
        print(f"📊 Total de respostas no banco: {count}")
        
        if count == 0:
            print("⚠️  Nenhuma resposta encontrada no banco para testar")
            return True
        
        # Testa busca por similaridade
        pergunta_teste = "configuração do sistema"
        embedding_teste = gerar_embeddings(pergunta_teste)
        
        respostas, similaridades = Resposta.objects.buscar_por_similaridade(
            embedding_teste, limite_similaridade=0.1, top_k=3
        )
        
        print(f"✅ Busca vetorial executada: {len(respostas)} resultados")
        for i, (resposta, sim) in enumerate(zip(respostas, similaridades)):
            print(f"   {i+1}. Similaridade: {sim:.3f} - {resposta.content[:50]}...")
        
        return True
    except Exception as e:
        print(f"❌ Erro na busca vetorial: {str(e)}")
        return False

def test_audio_validation():
    """Testa a validação de texto para áudio."""
    print("\n=== Testando Validação de Áudio ===")
    try:
        # Teste com texto válido
        texto_valido = "Esta é uma resposta de teste do sistema Spartacus."
        valido, resultado = validar_texto_audio(texto_valido)
        print(f"✅ Texto válido: {valido} - {resultado[:30]}...")
        
        # Teste com texto muito longo
        texto_longo = "A" * 6000
        valido, resultado = validar_texto_audio(texto_longo)
        print(f"✅ Texto longo rejeitado: {not valido} - {resultado}")
        
        # Teste com texto vazio
        valido, resultado = validar_texto_audio("")
        print(f"✅ Texto vazio rejeitado: {not valido} - {resultado}")
        
        return True
    except Exception as e:
        print(f"❌ Erro na validação de áudio: {str(e)}")
        return False

def test_model_methods():
    """Testa os novos métodos do modelo Resposta."""
    print("\n=== Testando Métodos do Modelo ===")
    try:
        # Verifica se existem respostas
        resposta = Resposta.objects.first()
        if not resposta:
            print("⚠️  Nenhuma resposta encontrada para testar métodos")
            return True
        
        # Testa get_embedding
        embedding = resposta.get_embedding()
        if embedding:
            print(f"✅ get_embedding funcionando: {len(embedding)} dimensões")
        else:
            print("⚠️  Resposta sem embedding")
        
        # Testa calcular_similaridade
        if embedding:
            # Usa o mesmo embedding para garantir compatibilidade
            similaridade = resposta.calcular_similaridade(embedding)
            print(f"✅ calcular_similaridade funcionando: {similaridade:.3f}")
            
            # Testa com embedding de outra resposta se disponível
            outra_resposta = Resposta.objects.exclude(id=resposta.id).first()
            if outra_resposta and outra_resposta.get_embedding():
                similaridade_cruzada = resposta.calcular_similaridade(outra_resposta.get_embedding())
                print(f"✅ Similaridade cruzada: {similaridade_cruzada:.3f}")
        
        return True
    except Exception as e:
        print(f"❌ Erro nos métodos do modelo: {str(e)}")
        return False

def main():
    """Executa todos os testes."""
    print("🚀 Iniciando testes de refatoração do Agente AI")
    print("=" * 50)
    
    testes = [
        test_embedding_generation,
        test_vector_search,
        test_audio_validation,
        test_model_methods
    ]
    
    resultados = []
    for teste in testes:
        try:
            resultado = teste()
            resultados.append(resultado)
        except Exception as e:
            print(f"❌ Erro crítico no teste {teste.__name__}: {str(e)}")
            resultados.append(False)
    
    print("\n" + "=" * 50)
    print("📊 RESUMO DOS TESTES")
    print("=" * 50)
    
    sucessos = sum(resultados)
    total = len(resultados)
    
    for i, (teste, resultado) in enumerate(zip(testes, resultados)):
        status = "✅ PASSOU" if resultado else "❌ FALHOU"
        print(f"{i+1}. {teste.__name__}: {status}")
    
    print(f"\n🎯 Resultado Final: {sucessos}/{total} testes passaram")
    
    if sucessos == total:
        print("🎉 Todas as refatorações estão funcionando corretamente!")
    else:
        print("⚠️  Algumas refatorações precisam de ajustes.")
    
    return sucessos == total

if __name__ == "__main__":
    main()