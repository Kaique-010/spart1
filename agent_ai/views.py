from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse
import requests
from bs4 import BeautifulSoup
import numpy as np
import re
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import Manual, Resposta
from .embedding import gerar_embeddings
import json


class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


def fetch_manual_content(manual):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(manual.url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        return None, f'Erro ao acessar a URL: {str(e)}'

    soup = BeautifulSoup(response.text, 'html.parser')
    ignorar = ['Spartacus | Sistemas', 'Todos os direitos reservados']
    content = ' '.join([p.get_text().strip() for p in soup.find_all('p') if not any(text in p for text in ignorar)])
    return content, None


#@api_view(['GET'])
#@permission_classes([IsAuthenticated])
def buscar_manual(request, manual_id):
    manual = get_object_or_404(Manual, id=manual_id)
    content, error = fetch_manual_content(manual)
    if error:
        return Response({'erro': error}, status=500)
    
    embeddings = gerar_embeddings(content)
    resposta, created = Resposta.objects.get_or_create(manual=manual, defaults={'content': content})
    if not created:
        resposta.content = content
        resposta.set_embedding(embeddings)
        resposta.save()
    
    return Response({'mensagem': 'Resposta gerada!', 'content': content})


#@api_view(['GET'])
#@permission_classes([IsAuthenticated])
def buscar_resposta(request, manual_id, query):
    manual = get_object_or_404(Manual, id=manual_id)
    
    resposta = Resposta.objects.filter(manual=manual).first()
    if not resposta:
        return Response({'response': 'Nenhuma resposta encontrada.'})
    
    query_embedding = gerar_embeddings(query)
    resposta_embedding = resposta.get_embedding()
    similarity = np.dot(query_embedding, resposta_embedding) / (np.linalg.norm(query_embedding) * np.linalg.norm(resposta_embedding))
    
    return Response({'response': resposta.content if similarity > 0.4 else 'Desculpe, não encontrei uma resposta relevante.'})


#@api_view(['POST'])
#@permission_classes([IsAuthenticated])
def perguntar_spart(request):
    data = json.loads(request.body)
    pergunta = data.get('pergunta', '').strip()
    if not pergunta:
        return Response({'resposta': 'A pergunta não pode estar vazia'}, status=400)
    
    respostas = Resposta.objects.all()
    paginator = CustomPagination()
    paginated_respostas = paginator.paginate_queryset(respostas, request)
    pergunta_embedding = gerar_embeddings(pergunta)
    melhor_resposta, melhor_similaridade = None, 0.0
    
    for resposta in paginated_respostas:
        resposta_embedding = resposta.get_embedding()
        similaridade = np.dot(pergunta_embedding / np.linalg.norm(pergunta_embedding), resposta_embedding / np.linalg.norm(resposta_embedding))
        if similaridade > melhor_similaridade:
            melhor_similaridade = similaridade
            melhor_resposta = resposta
    
    if melhor_similaridade > 0.5:
        return Response({'resposta': melhor_resposta.content, 'manual': melhor_resposta.manual.url})
    
    return Response({'resposta': 'Não encontrei uma resposta adequada.', 'central': 'https://spartacus.movidesk.com/kb/'})



def spartacus_view(request):
    return render(request, "agent_ai/spartacus.html")
