#!/usr/bin/env python
"""
Script para testar o sistema de memória conversacional do Spartacus AI.

Este script testa:
1. Criação de nova conversa
2. Continuidade da conversa com session_id
3. Recuperação do histórico
4. Contexto de memória
"""

import requests
import json
import time

# URL base da API
BASE_URL = "http://localhost:8000/api"

def testar_memoria_conversacional():
    print("=== TESTE DO SISTEMA DE MEMÓRIA CONVERSACIONAL ===")
    print()
    
    # Teste 1: Primeira pergunta (nova conversa)
    print("1. Testando primeira pergunta (nova conversa)...")
    response1 = requests.post(
        f"{BASE_URL}/perguntar/",
        json={"pergunta": "Olá, meu nome é João. Como faço para cadastrar um cliente no Spartacus?"}
    )
    
    if response1.status_code == 200:
        data1 = response1.json()
        session_id = data1.get('session_id')
        print(f"✓ Session ID criado: {session_id}")
        print(f"✓ Resposta: {data1.get('resposta')[:100]}...")
        print()
    else:
        print(f"✗ Erro na primeira pergunta: {response1.status_code}")
        return
    
    # Aguarda um pouco
    time.sleep(2)
    
    # Teste 2: Segunda pergunta com session_id (deve lembrar do nome)
    print("2. Testando segunda pergunta com memória...")
    response2 = requests.post(
        f"{BASE_URL}/perguntar/",
        json={
            "pergunta": "Você lembra qual é o meu nome?",
            "session_id": session_id
        }
    )
    
    if response2.status_code == 200:
        data2 = response2.json()
        print(f"✓ Resposta: {data2.get('resposta')}")
        print()
    else:
        print(f"✗ Erro na segunda pergunta: {response2.status_code}")
        return
    
    # Aguarda um pouco
    time.sleep(2)
    
    # Teste 3: Terceira pergunta sobre contexto anterior
    print("3. Testando continuidade da conversa...")
    response3 = requests.post(
        f"{BASE_URL}/perguntar/",
        json={
            "pergunta": "E sobre aquela pergunta que fiz sobre cadastro de cliente, você pode dar mais detalhes?",
            "session_id": session_id
        }
    )
    
    if response3.status_code == 200:
        data3 = response3.json()
        print(f"✓ Resposta: {data3.get('resposta')[:150]}...")
        print()
    else:
        print(f"✗ Erro na terceira pergunta: {response3.status_code}")
        return
    
    # Teste 4: Nova conversa (sem session_id)
    print("4. Testando nova conversa (sem session_id)...")
    response4 = requests.post(
        f"{BASE_URL}/perguntar/",
        json={"pergunta": "Qual é o meu nome?"}
    )
    
    if response4.status_code == 200:
        data4 = response4.json()
        new_session_id = data4.get('session_id')
        print(f"✓ Novo Session ID: {new_session_id}")
        print(f"✓ Resposta (não deve lembrar do nome): {data4.get('resposta')}")
        print()
    else:
        print(f"✗ Erro na quarta pergunta: {response4.status_code}")
        return
    
    print("=== TESTE CONCLUÍDO COM SUCESSO! ===")
    print(f"Session ID da primeira conversa: {session_id}")
    print(f"Session ID da nova conversa: {new_session_id}")

if __name__ == "__main__":
    try:
        testar_memoria_conversacional()
    except requests.exceptions.ConnectionError:
        print("✗ Erro: Não foi possível conectar ao servidor.")
        print("Certifique-se de que o servidor Django está rodando em http://localhost:8000")
    except Exception as e:
        print(f"✗ Erro inesperado: {e}")