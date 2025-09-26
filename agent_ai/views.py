from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse, StreamingHttpResponse
import requests
from bs4 import BeautifulSoup
import numpy as np
import re
from agent_ai.utils import criar_audio, criar_audio_async, validar_texto_audio
from .models import Manual, Resposta, Conversa, Mensagem, ManualProcessado
from .embedding import gerar_embeddings
from django.views.decorators.csrf import csrf_exempt
import json
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# 🔹 Buscar conteúdo do manual e gerar embeddings
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




def buscar_contexto_relevante(pergunta, limite_similaridade=0.4, top_k=3):
    """Busca o contexto mais relevante para a pergunta em manuais processados e respostas antigas."""
    pergunta_embedding = gerar_embeddings(pergunta)
    
    if pergunta_embedding is None:
        return None, 0.0
    
    # Busca primeiro nos manuais processados (prioridade)
    manual_processado, similaridade_manual = ManualProcessado.objects.buscar_melhor_manual(
        pergunta_embedding, limite_similaridade
    )
    
    # Busca também nas respostas antigas
    resposta, similaridade_resposta = Resposta.objects.buscar_melhor_resposta(
        pergunta_embedding, limite_similaridade
    )
    
    # Retorna o contexto com maior similaridade
    if manual_processado and resposta:
        if similaridade_manual >= similaridade_resposta:
            return manual_processado, similaridade_manual
        else:
            return resposta, similaridade_resposta
    elif manual_processado:
        return manual_processado, similaridade_manual
    elif resposta:
        return resposta, similaridade_resposta
    
    return None, 0.0


def obter_ou_criar_conversa(session_id=None):
    """Obtém uma conversa existente ou cria uma nova."""
    if session_id:
        try:
            conversa = Conversa.objects.get(session_id=session_id, ativa=True)
            return conversa
        except Conversa.DoesNotExist:
            pass
    
    # Cria nova conversa
    conversa = Conversa.objects.create()
    return conversa


def salvar_mensagem(conversa, tipo, conteudo, resposta_relacionada=None, similaridade=None):
    """Salva uma mensagem na conversa."""
    return Mensagem.objects.create(
        conversa=conversa,
        tipo=tipo,
        conteudo=conteudo,
        resposta_relacionada=resposta_relacionada,
        similaridade=similaridade
    )


def buscar_multiplos_contextos(pergunta, limite_similaridade=0.4, top_k=3):
    """Busca múltiplos contextos relevantes para respostas mais completas."""
    pergunta_embedding = gerar_embeddings(pergunta)
    
    respostas, similaridades = Resposta.objects.buscar_por_similaridade(
        pergunta_embedding, limite_similaridade, top_k
    )
    
    return list(zip(respostas, similaridades)) if respostas else []


@csrf_exempt
def perguntar_spart_stream(request):
    """Endpoint com streaming e sistema de memória para respostas do GPT."""
    if request.method != "POST":
        return JsonResponse({'erro': 'Método inválido'}, status=405)

    data = json.loads(request.body)
    pergunta = data.get('pergunta', '').strip()
    session_id = data.get('session_id')

    if not pergunta:
        return JsonResponse({'resposta': 'A pergunta não pode estar vazia'}, status=400)
    
    # Obtém ou cria conversa
    conversa = obter_ou_criar_conversa(session_id)
    
    # Salva a pergunta do usuário
    salvar_mensagem(conversa, 'pergunta', pergunta)

    # Busca contexto relevante
    contexto, similaridade = buscar_contexto_relevante(pergunta)
    
    def generate_response():
        try:
            # Obtém contexto de memória da conversa
            contexto_memoria = conversa.get_contexto_memoria(limite=6)
            
            if contexto and similaridade > 0.4:
                # Obtém o conteúdo do contexto (pode ser ManualProcessado ou Resposta)
                if hasattr(contexto, 'conteudo_markdown'):
                    # É um ManualProcessado
                    conteudo_contexto = contexto.conteudo_markdown[:1500]
                    fonte_contexto = f"Manual: {contexto.titulo}"
                    url_manual = contexto.url_original
                    # Obtém imagens relacionadas ao manual
                    imagens_relacionadas = list(contexto.imagens.all()[:5])  # Máximo 5 imagens
                else:
                    # É uma Resposta - buscar imagens do manual relacionado
                    conteudo_contexto = contexto.content[:1500]
                    fonte_contexto = f"Manual: {contexto.manual.title}"
                    url_manual = contexto.manual.url
                    # Buscar o ManualProcessado correspondente para obter as imagens
                    try:
                        from .models import ManualProcessado
                        manual_processado = ManualProcessado.objects.get(manual_id=contexto.manual.id)
                        imagens_relacionadas = list(manual_processado.imagens.all()[:5])  # Máximo 5 imagens
                    except ManualProcessado.DoesNotExist:
                        imagens_relacionadas = []
                
                # Monta prompt com contexto
                # Verifica se há imagens disponíveis para mencionar na resposta
                tem_imagens = len(imagens_relacionadas) > 0
                instrucao_imagens = "- Se houver referências a imagens no contexto (<!-- image:id -->), mencione que existem imagens ilustrativas disponíveis" if not tem_imagens else "- Mencione que há imagens ilustrativas disponíveis que complementam a explicação"
                
                prompt = f"""Você é o Spartacus AI, assistente especializado no sistema Spartacus ERP.
                
INSTRUÇÕES:
                - Use APENAS as informações do contexto fornecido
                - Seja claro, objetivo e didático
                - Organize a resposta em passos numerados quando apropriado
                - Não repita informações desnecessariamente
                - Mantenha um tom profissional e amigável
                - Considere o histórico da conversa para dar continuidade
                {instrucao_imagens}
                
                CONTEXTO DO SISTEMA ({fonte_contexto}): {conteudo_contexto}
                
                HISTÓRICO DA CONVERSA:
                {contexto_memoria}
                
                PERGUNTA ATUAL: {pergunta}
                
                RESPOSTA (seja conciso e direto):"""
            else:
                # Resposta genérica quando não há contexto suficiente
                prompt = f"""Você é o Spartacus AI, assistente do sistema Spartacus ERP.
                
                HISTÓRICO DA CONVERSA:
                {contexto_memoria}
                
                O usuário perguntou: "{pergunta}"
                
                Responda de forma educada que você não encontrou informações específicas sobre essa pergunta na base de conhecimento atual. Sugira que consulte a central de ajuda oficial do Spartacus.
                
                Seja breve e direto:"""
            
            # Stream da resposta do GPT
            stream = client.chat.completions.create(
                 model="gpt-3.5-turbo",
                 messages=[
                     {"role": "system", "content": "Você é um assistente especializado em ERP Spartacus. Seja sempre conciso, claro e evite repetições."},
                     {"role": "user", "content": prompt}
                 ],
                 stream=True,
                 max_tokens=400,
                 temperature=0.3
             )
             
            resposta_completa = ""
            for chunk in stream:
                 if chunk.choices[0].delta.content is not None:
                     content = chunk.choices[0].delta.content
                     resposta_completa += content
                     yield f"data: {json.dumps({'content': content})}\n\n"
             
             # Salva a resposta na conversa
            if resposta_completa.strip():
                 salvar_mensagem(
                     conversa, 
                     'resposta', 
                     resposta_completa, 
                     resposta_relacionada=contexto,
                     similaridade=similaridade
                 )
             
             # Gera áudio da resposta completa de forma assíncrona (TEMPORARIAMENTE DESABILITADO)
            # if resposta_completa.strip():
            #      valido, texto_limpo = validar_texto_audio(resposta_completa)
            #      if valido:
            #          def audio_callback(audio_url):
            #              if audio_url:
            #                  # Aqui você poderia salvar a URL do áudio no banco ou cache
            #                  pass
            #          
            #          criar_audio_async(texto_limpo, callback=audio_callback)
             
             # Prepara informações das imagens para o frontend
            imagens_info = []
            if contexto and 'imagens_relacionadas' in locals() and imagens_relacionadas:
                for imagem in imagens_relacionadas:
                    imagens_info.append({
                        'url': imagem.get_url_servida(),
                        'alt_text': imagem.alt_text,
                        'nome_arquivo': imagem.nome_arquivo,
                        'ordem': imagem.ordem
                    })
             
             # Sinal de fim do stream com imagens
            final_data = {
                'done': True, 
                'similaridade': float(similaridade), 
                'session_id': str(conversa.session_id)
            }
            if imagens_info:
                final_data['imagens'] = imagens_info
            
            yield f"data: {json.dumps(final_data)}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    response = StreamingHttpResponse(generate_response(), content_type='text/plain')
    response['Cache-Control'] = 'no-cache'
    return response


@csrf_exempt
def perguntar_spart(request):
    """Versão não-streaming com sistema de memória."""
    if request.method != "POST":
        return JsonResponse({'erro': 'Método inválido'}, status=405)

    data = json.loads(request.body)
    pergunta = data.get('pergunta', '').strip()
    session_id = data.get('session_id')

    if not pergunta:
        return JsonResponse({'resposta': 'A pergunta não pode estar vazia'}, status=400)

    # Obtém ou cria conversa
    conversa = obter_ou_criar_conversa(session_id)
    
    # Salva a pergunta do usuário
    salvar_mensagem(conversa, 'pergunta', pergunta)
    
    # Busca contexto relevante
    contexto, similaridade = buscar_contexto_relevante(pergunta)
    
    try:
        # Obtém contexto de memória da conversa
        contexto_memoria = conversa.get_contexto_memoria(limite=6)
        
        if contexto and similaridade > 0.4:
            # Obtém o conteúdo do contexto (pode ser ManualProcessado ou Resposta)
                if hasattr(contexto, 'conteudo_markdown'):
                    # É um ManualProcessado
                    conteudo_contexto = contexto.conteudo_markdown[:1500]
                    fonte_contexto = f"Manual: {contexto.titulo}"
                    url_manual = contexto.url_original
                    # Obtém imagens relacionadas ao manual e passa ao contexto da resposta
                    imagens_relacionadas = list(contexto.imagens.all()[:10])  # Máximo 10 imagens
                else:
                    # É uma Resposta
                    conteudo_contexto = contexto.content[:1500]
                    fonte_contexto = f"Manual: {contexto.manual.title}"
                    url_manual = contexto.manual.url
                    imagens_relacionadas = []
            
                # Verifica se há imagens disponíveis para mencionar na resposta
                tem_imagens = len(imagens_relacionadas) > 0
                instrucao_imagens = "- Se houver referências a imagens no contexto (<!-- image:id -->), mencione que existem imagens ilustrativas disponíveis" if not tem_imagens else "- Mencione que há imagens ilustrativas disponíveis que complementam a explicação"
            
                prompt = f"""Você é o Spartacus AI, assistente especializado no sistema Spartacus ERP.
                
INSTRUÇÕES:
                - Use APENAS as informações do contexto fornecido
                - Seja claro, objetivo e didático
                - Organize a resposta em passos numerados quando apropriado
                - Não repita informações desnecessariamente
                - Mantenha um tom profissional e amigável
                - Considere o histórico da conversa para dar continuidade
                {instrucao_imagens}
            
            CONTEXTO DO SISTEMA ({fonte_contexto}): {conteudo_contexto}
            
            HISTÓRICO DA CONVERSA:
            {contexto_memoria}
            
            PERGUNTA ATUAL: {pergunta}
            
            RESPOSTA (seja conciso e direto):"""
        else:
            prompt = f"""Você é o Spartacus AI, assistente do sistema Spartacus ERP.
            
            HISTÓRICO DA CONVERSA:
            {contexto_memoria}
            
            O usuário perguntou: "{pergunta}"
            
            Responda de forma educada que você não encontrou informações específicas sobre essa pergunta na base de conhecimento atual. Sugira que consulte a central de ajuda oficial do Spartacus.
            
            Seja breve e direto:
            
            no fim das suas repostas sempre indique a central de ajuda oficial do Spartacus:  https://spartacus.movidesk.com/kb/'
            """
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Você é um assistente especializado em ERP Spartacus. Seja sempre conciso, claro e evite repetições."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=600,
            temperature=0.3
        )
        
        resposta_gpt = response.choices[0].message.content.strip()
        
        # Salva a resposta na conversa
        salvar_mensagem(
            conversa, 
            'resposta', 
            resposta_gpt, 
            resposta_relacionada=contexto,
            similaridade=similaridade
        )
        
        # Gera áudio da resposta (TEMPORARIAMENTE DESABILITADO PARA PERFORMANCE)
        audio_url = None
        # if resposta_gpt:
        #     valido, texto_limpo = validar_texto_audio(resposta_gpt)
        #     if valido:
        #         audio_url = criar_audio(texto_limpo)
        
        # Prepara informações das imagens para o frontend
        imagens_info = []
        if contexto and hasattr(contexto, 'conteudo_markdown') and imagens_relacionadas:
            for imagem in imagens_relacionadas:
                imagens_info.append({
                    'url': imagem.get_url_servida(),
                    'alt_text': imagem.alt_text,
                    'nome_arquivo': imagem.nome_arquivo,
                    'ordem': imagem.ordem
                })
        
        return JsonResponse({
            'resposta': resposta_gpt,
            'similaridade': float(similaridade),
            'manual': url_manual if contexto else None,
            'feedback': 'Resposta gerada com IA baseada no conhecimento do sistema.',
            'audio_url': audio_url,
            'session_id': str(conversa.session_id),
            'imagens': imagens_info
        })
        
    except Exception as e:
        return JsonResponse({
            'resposta': 'Desculpe, ocorreu um erro ao processar sua pergunta.',
            'erro': str(e),
            'central': 'Caso precise de ajuda, consulte: https://spartacus.movidesk.com/kb/',
        }, status=500)


def spartacus_view(request):
    return render(request, "agent_ai/spartacus.html")