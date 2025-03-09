from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse
import requests
from bs4 import BeautifulSoup
import numpy as np
from .models import Manual, Resposta
from .embedding import gerar_embeddings
from django.views.decorators.csrf import csrf_exempt
import json


#Função para buscar os manuais e gerar os embeddings e respostas 
def buscar_manual(request, manual_id):
    print(f"Iniciando a busca do conteúdo para o Manual ID {manual_id}...")

    manual = get_object_or_404(Manual, id=manual_id)
    print(f"Manual encontrado: {manual.title}")
    headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
    }
    # Faz scraping do conteúdo do manual
    response = requests.get(manual.url, headers=headers, verify=False)

    
    # Verificar o código se for ok retorna 200 com o manual para tratar os dados 
    if response.status_code != 200:
        print(f"Erro ao acessar a URL {manual.url}: Código de status {response.status_code}")
        return JsonResponse({'erro': f'Falha ao acessar a URL do manual: {response.status_code}'}, status=500)
   
    #com o beautifulsoup pega o conteudo do html nos paragrafos e extrais
    
    soup = BeautifulSoup(response.text, 'html.parser')
    content = ' '.join([p.get_text() for p in soup.find_all('p')])


    print(f"Conteúdo extraído: {content[:200]}...")

    #se não tiver conteudo retornar a mensagem de erro 
    if not content:
        print("Nenhum conteúdo encontrado na URL.")
        return JsonResponse({'erro': 'Nenhum conteúdo encontrado na URL'}, status=404)

    # Gera embeddingsa partir do conteúdo do url 
    print("Gerando embeddings para o conteúdo extraído...")
    embeddings = gerar_embeddings(content)

    # Salva a resposta no banco (cria ou atualiza)
    resposta, created = Resposta.objects.get_or_create(manual=manual)
    resposta.content = content
    resposta.set_embedding(embeddings)
    resposta.save()

    print(f"Resposta salva com sucesso. Embeddings gerados: {embeddings.tolist()[:5]}...")

    
    #faz o retorno para o banco com a resposta dos embeddings gerados 
    
    return JsonResponse({
        'mensagem': 'Resposta gerada com sucesso!',
        'content': content,
        'embeddings': embeddings.tolist(),
    })



def buscar_resposta(request, manual_id, query):
    manual = get_object_or_404(Manual, id=manual_id)
    resposta = Resposta.objects.filter(manual=manual).first()

    if not resposta:
        return JsonResponse({'response': 'Nenhuma resposta encontrada.'})

    # Gera embedding para a pergunta do usuário
    query_embedding = gerar_embeddings(query)

    # Calcula a similaridade com a resposta armazenada
    resposta_embedding = resposta.get_embedding()
    similarity = np.dot(query_embedding, resposta_embedding) / (np.linalg.norm(query_embedding) * np.linalg.norm(resposta_embedding))

    if similarity > 0.4:  # Ajuste conforme necessário
        return JsonResponse({'response': resposta.content})

    return JsonResponse({'response': 'Desculpe, não encontrei uma resposta relevante.'})





@csrf_exempt
def perguntar_spart(request):
    """Recebe a pergunta do usuário e retorna a resposta mais relevante."""
    if request.method != "POST":
        return JsonResponse({'erro': 'Método inválido'}, status=405)

    data = json.loads(request.body)
    pergunta = data.get('pergunta', '').strip()

    if not pergunta:
        return JsonResponse({'resposta': 'A pergunta não pode estar vazia'}, status=400)

    respostas = Resposta.objects.all()

    if not respostas.exists():
        return JsonResponse({'resposta': 'Nenhuma resposta encontrada.'})

    pergunta_embedding = gerar_embeddings(pergunta)
    melhor_resposta = None
    melhor_similaridade = 0.0

    for resposta in respostas:
        resposta_embedding = resposta.get_embedding()
        similaridade = np.dot(pergunta_embedding, resposta_embedding) / (
            np.linalg.norm(pergunta_embedding) * np.linalg.norm(resposta_embedding))

        if similaridade > melhor_similaridade:
            melhor_similaridade = similaridade
            melhor_resposta = resposta

    if melhor_similaridade > 0.4:
        return JsonResponse({'resposta': melhor_resposta.content})

    return JsonResponse({'resposta': 'Desculpe, não entendi, tenta com outras palavras, por favor.'})


def spartacus_view(request):
    return render(request, "agent_ai/spartacus.html")