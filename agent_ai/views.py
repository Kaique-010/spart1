from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse
import requests
from bs4 import BeautifulSoup
import numpy as np
import re
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

from agent_ai.utils import criar_audio
from .models import Manual, Resposta
from .embedding import gerar_embeddings
from django.views.decorators.csrf import csrf_exempt
import json



def buscar_manual(request, manual_id):
    print(f"Iniciando a busca do conteúdo para o Manual ID {manual_id}...")

    manual = get_object_or_404(Manual, id=manual_id)
    print(f"Manual encontrado: {manual.title}")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
    }

    response = requests.get(manual.url, headers=headers, verify=False)

    if response.status_code != 200:
        print(f"Erro ao acessar a URL {manual.url}: Código de status {response.status_code}")
        return JsonResponse({'erro': f'Falha ao acessar a URL do manual: {response.status_code}'}, status=500)

    soup = BeautifulSoup(response.text, 'html.parser')

    # Lista de palavras a serem ignorados
    ignorar = [
        'Spartacus | Sistemas para Gestão Empresarial, Contábil e Logística.',
        'R. Brasil Pinheiro, 268 - Ponta Grossa - PR',
        '+55 (42) 3223-6164 | +55 (42) 3223-0774 | +55 (42) 8822-4085',
        'Todos os direitos reservados. Copyright ©2023 SPARTACUS',
        'Todos os direitos reservados. Copyright ©2023',
    ]

    # 🔹 Extrair texto e remover textos indesejados
    paragrafos = [p.get_text().strip() for p in soup.find_all('p')]
    content = '  \n\n'.join([p for p in paragrafos if not any(ignorado in p for ignorado in ignorar)])
    
    content = re.sub(r'(\. )([A-Z])', r'.\n\n\2', content)

    
    '''
    # 🔹 Extrair URLs das imagens
    image_urls = [img['src'] for img in soup.find_all('img') if img.get('src')]

   
    # 🔹 Processar imagens com OCR
    image_texts = []
    for img_url in image_urls:
        try:
            img_response = requests.get(img_url, stream=True)
            if img_response.status_code == 200:
                image = Image.open(BytesIO(img_response.content))
                image = image.convert("RGB")  # 🛠 Converter para RGB (evita erro com transparências)
                extracted_text = pytesseract.image_to_string(image, lang="por")  # 🏆 Melhor OCR em português

                if extracted_text.strip():
                    image_texts.append(extracted_text)

        except Exception as e:
            print(f"Erro ao processar imagem {img_url}: {e}")
            '''

    # 🔹 Concatenar conteúdo extraído (texto + imagens OCR)
    full_content = content + " " + " "#join(image_texts)


    if not full_content.strip():
        return JsonResponse({'erro': 'Nenhum conteúdo encontrado na URL'}, status=404)

    embeddings = gerar_embeddings(full_content)

    resposta, created = Resposta.objects.get_or_create(manual=manual)
    resposta.content = full_content
    resposta.set_embedding(embeddings)
    resposta.save()

    return JsonResponse({
        'mensagem': 'Resposta gerada com sucesso!',
        'content': full_content,
        'embeddings': embeddings.tolist(),
        #'image_urls': image_urls
    })



def buscar_resposta(request, manual_id, query):
    manual = get_object_or_404(Manual, id=manual_id)
    resposta = Resposta.objects.filter(manual=manual).first()

    if not resposta:
        return JsonResponse({'response': 'Nenhuma resposta encontrada.'})


    query_embedding = gerar_embeddings(query)


    resposta_embedding = resposta.get_embedding()
    similarity = np.dot(query_embedding, resposta_embedding) / (np.linalg.norm(query_embedding) * np.linalg.norm(resposta_embedding))

    if similarity > 0.4:  
        return JsonResponse({'response': resposta.content})

    return JsonResponse({'response': 'Desculpe, não encontrei uma resposta relevante.'})




@csrf_exempt
def perguntar_spart(request):
    """Recebe a pergunta do usuário e retorna a melhor resposta baseada em similaridade de embeddings."""
    if request.method != "POST":
        return JsonResponse({'erro': 'Método inválido'}, status=405)

    data = json.loads(request.body)
    pergunta = data.get('pergunta', '').strip()

    if not pergunta:
        return JsonResponse({'resposta': 'A pergunta não pode estar vazia'}, status=400)

    respostas = Resposta.objects.all()
    if not respostas.exists():
        return JsonResponse({'resposta': 'Nenhuma resposta encontrada.'})

    # Gera embedding da pergunta
    pergunta_embedding = gerar_embeddings(pergunta)
    melhor_resposta = None
    melhor_similaridade = 0.0

    for resposta in respostas:
        resposta_embedding = resposta.get_embedding()

        # Normaliza os vetores antes do cálculo da similaridade
        pergunta_embedding = pergunta_embedding / np.linalg.norm(pergunta_embedding)
        resposta_embedding = resposta_embedding / np.linalg.norm(resposta_embedding)

        similaridade = np.dot(pergunta_embedding, resposta_embedding)

        if similaridade > melhor_similaridade:
            melhor_similaridade = similaridade
            melhor_resposta = resposta
    
    audio_url = criar_audio(str(melhor_resposta.content))    

    if melhor_similaridade > 0.5:
        return JsonResponse({
       
            'resposta': f'Para a Sua pergunta encontrei essa como a melhor resposta:\n{melhor_resposta.content}',
            'manual':f'{melhor_resposta.manual.url}',
            'feedback': 'Essa é a melhor resposta que encontrei para sua pergunta.',
            'sugestao': 'Se não for isso, tente fornecer mais detalhes para eu te ajudar melhor.',
            'audio_url': audio_url
            
        })
        


    return JsonResponse({
    
        'resposta': 'Desculpe, não entendi bem sua pergunta.',
        'feedback': 'Essa é a melhor resposta que encontrei para sua pergunta.',
        'sugestao': 'Se não for isso, tente fornecer mais detalhes para eu te ajudar melhor.',
        'central': 'Caso queria pode dar uma olhadinha na nossa central de ajuda: https://spartacus.movidesk.com/kb/',

         
    })


def spartacus_view(request):
    return render(request, "agent_ai/spartacus.html")