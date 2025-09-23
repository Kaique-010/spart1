from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import StreamingHttpResponse
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.openapi import AutoSchema
from .models import Manual, Resposta, ManualProcessado, ImagemManual
from .serializers import (
    ManualSerializer, RespostaSerializer, PerguntaSerializer,
    RespostaAgentSerializer, StreamResponseSerializer,
    BuscarManualSerializer, BuscarRespostaSerializer
)
from .views import (
    buscar_manual, buscar_resposta, perguntar_spart, 
    perguntar_spart_stream
)
import json

class ManualViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para gerenciar manuais do sistema Spartacus.
    
    Permite listar e visualizar manuais cadastrados no sistema.
    """
    queryset = Manual.objects.all().order_by('-created_at')
    serializer_class = ManualSerializer
    
    @extend_schema(
        summary="Buscar conteúdo do manual",
        description="Extrai o conteúdo de um manual específico e gera embeddings para busca vetorial.",
        responses={200: BuscarManualSerializer, 404: 'Manual não encontrado', 500: 'Erro ao processar manual'},
        examples=[
            OpenApiExample(
                'Sucesso',
                value={
                    'mensagem': 'Resposta gerada com sucesso!',
                    'content': 'Conteúdo extraído do manual...',
                    'embeddings': [0.1, 0.2, 0.3, '...']
                }
            )
        ]
    )
    @action(detail=True, methods=['post'])
    def buscar_conteudo(self, request, pk=None):
        """Busca e processa o conteúdo de um manual específico."""
        try:
            # Reutiliza a função existente
            response = buscar_manual(request, pk)
            if hasattr(response, 'content'):
                data = json.loads(response.content)
                return Response(data, status=response.status_code)
            return response
        except Exception as e:
            return Response(
                {'erro': f'Erro interno: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        summary="Buscar resposta por query",
        description="Busca uma resposta específica no manual usando uma query de texto.",
        parameters=[
            OpenApiParameter(
                name='query',
                description='Texto da consulta para busca',
                required=True,
                type=str,
                location=OpenApiParameter.PATH
            )
        ],
        responses={200: BuscarRespostaSerializer},
        examples=[
            OpenApiExample(
                'Resposta encontrada',
                value={'response': 'Resposta detalhada sobre a consulta...'}
            ),
            OpenApiExample(
                'Nenhuma resposta',
                value={'response': 'Desculpe, não encontrei uma resposta relevante.'}
            )
        ]
    )
    @action(detail=True, methods=['get'], url_path='resposta/(?P<query>[^/.]+)')
    def buscar_resposta_query(self, request, pk=None, query=None):
        """Busca resposta usando uma query específica."""
        try:
            response = buscar_resposta(request, pk, query)
            if hasattr(response, 'content'):
                data = json.loads(response.content)
                return Response(data, status=response.status_code)
            return response
        except Exception as e:
            return Response(
                {'response': f'Erro ao buscar resposta: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class RespostaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para visualizar respostas armazenadas no sistema.
    
    Permite listar e visualizar respostas com seus embeddings.
    """
    queryset = Resposta.objects.all().order_by('-created_at')
    serializer_class = RespostaSerializer

class AgenteAIViewSet(viewsets.ViewSet):
    """
    ViewSet principal para interação com o Agente AI Spartacus.
    
    Fornece endpoints para fazer perguntas ao agente e receber respostas
    baseadas em busca vetorial e processamento com GPT.
    """
    
    @extend_schema(
        summary="Perguntar ao Agente (Versão Padrão)",
        description="""
        Envia uma pergunta ao agente AI e recebe uma resposta completa.
        
        O agente utiliza:
        - Busca vetorial para encontrar contexto relevante
        - GPT-3.5-turbo para gerar respostas contextualizadas
        - Geração automática de áudio (quando possível)
        
        **Fluxo de processamento:**
        1. Recebe a pergunta do usuário
        2. Gera embedding da pergunta
        3. Busca contexto similar no banco de dados
        4. Gera resposta usando GPT com contexto encontrado
        5. Cria arquivo de áudio da resposta
        6. Retorna resposta completa com metadados
        """,
        request=PerguntaSerializer,
        responses={
            200: RespostaAgentSerializer,
            400: 'Pergunta inválida',
            500: 'Erro interno do servidor'
        },
        examples=[
            OpenApiExample(
                'Pergunta de exemplo',
                request_only=True,
                value={'pergunta': 'Como fazer backup no sistema Spartacus?'}
            ),
            OpenApiExample(
                'Resposta com contexto',
                response_only=True,
                value={
                    'resposta': 'Para fazer backup no sistema Spartacus, acesse...',
                    'similaridade': 0.85,
                    'manual': 'https://spartacus.movidesk.com/kb/article/123',
                    'feedback': 'Resposta gerada com IA baseada no conhecimento do sistema.',
                    'audio_url': '/media/audio/audio_abc123.mp3'
                }
            ),
            OpenApiExample(
                'Resposta sem contexto',
                response_only=True,
                value={
                    'resposta': 'Não encontrei informações específicas sobre essa pergunta...',
                    'similaridade': 0.2,
                    'manual': None,
                    'feedback': 'Resposta gerada com IA baseada no conhecimento do sistema.',
                    'central': 'Caso precise de ajuda, consulte: https://spartacus.movidesk.com/kb/'
                }
            )
        ]
    )
    @action(detail=False, methods=['post'])
    def perguntar(self, request):
        """Endpoint principal para perguntas ao agente."""
        serializer = PerguntaSerializer(data=request.data)
        if serializer.is_valid():
            try:
                from .views import (
                    buscar_contexto_relevante, obter_ou_criar_conversa, 
                    salvar_mensagem, client
                )
                from .utils import criar_audio, validar_texto_audio
                
                pergunta = serializer.validated_data['pergunta']
                session_id = serializer.validated_data.get('session_id')
                
                # Obtém ou cria conversa
                conversa = obter_ou_criar_conversa(session_id)
                
                # Salva a pergunta do usuário
                salvar_mensagem(conversa, 'pergunta', pergunta)
                
                # Busca contexto relevante
                contexto, similaridade = buscar_contexto_relevante(pergunta)
                
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
                    url_manual = None
                    prompt = f"""Você é o Spartacus AI, assistente do sistema Spartacus ERP.
                    
                    HISTÓRICO DA CONVERSA:
                    {contexto_memoria}
                    
                    O usuário perguntou: "{pergunta}"
                    
                    Responda de forma educada que você não encontrou informações específicas sobre essa pergunta na base de conhecimento atual. Sugira que consulte a central de ajuda oficial do Spartacus.
                    
                    Seja breve e direto:"""
                
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "Você é um assistente especializado em ERP Spartacus. Seja sempre conciso, claro e evite repetições."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=400,
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
                return Response(
                    {
                        'resposta': 'Desculpe, ocorreu um erro ao processar sua pergunta.',
                        'erro': str(e),
                        'central': 'Caso precise de ajuda, consulte: https://spartacus.movidesk.com/kb/'
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Perguntar ao Agente (Versão Streaming)",
        description="""
        Versão com streaming em tempo real das respostas do agente AI.
        
        **Características:**
        - Respostas em tempo real (Server-Sent Events)
        - Menor latência percebida pelo usuário
        - Geração de áudio assíncrona
        - Ideal para interfaces interativas
        
        **Formato da resposta:**
        - Content-Type: text/plain
        - Formato: Server-Sent Events (SSE)
        - Cada chunk contém JSON com 'content' ou 'done'
        
        **Exemplo de stream:**
        ```
        data: {"content": "Para fazer"}
        data: {"content": " backup no"}
        data: {"content": " sistema..."}
        data: {"done": true, "similaridade": 0.85}
        ```
        """,
        request=PerguntaSerializer,
        responses={
            200: 'Stream de dados (text/plain)',
            400: 'Pergunta inválida',
            500: 'Erro interno do servidor'
        },
        examples=[
            OpenApiExample(
                'Pergunta para streaming',
                request_only=True,
                value={'pergunta': 'Como configurar usuários no Spartacus?'}
            )
        ]
    )
    @action(detail=False, methods=['post'])
    def perguntar_stream(self, request):
        """Endpoint com streaming para respostas em tempo real."""
        serializer = PerguntaSerializer(data=request.data)
        if serializer.is_valid():
            try:
                # Reutiliza a função existente de streaming
                return perguntar_spart_stream(request)
            except Exception as e:
                return Response(
                    {'error': f'Erro no streaming: {str(e)}'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Status da API",
        description="Verifica o status e saúde da API do agente.",
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'status': {'type': 'string', 'example': 'online'},
                    'version': {'type': 'string', 'example': '1.0.0'},
                    'endpoints': {
                        'type': 'object',
                        'properties': {
                            'perguntar': {'type': 'string'},
                            'perguntar_stream': {'type': 'string'},
                            'manuais': {'type': 'string'}
                        }
                    },
                    'features': {
                        'type': 'array',
                        'items': {'type': 'string'}
                    }
                }
            }
        }
    )
    @action(detail=False, methods=['get'])
    def status(self, request):
        """Retorna informações sobre o status da API."""
        return Response({
            'status': 'online',
            'version': '1.0.0',
            'description': 'API do Agente AI Spartacus - Sistema de assistente virtual com busca vetorial',
            'endpoints': {
                'perguntar': '/api/agente/perguntar/',
                'perguntar_stream': '/api/agente/perguntar_stream/',
                'manuais': '/api/manuais/',
                'respostas': '/api/respostas/'
            },
            'features': [
                'Busca vetorial com embeddings',
                'Integração GPT-3.5-turbo',
                'Geração de áudio automática',
                'Streaming de respostas em tempo real',
                'Processamento de manuais web'
            ],
            'models': {
                'embedding': 'text-embedding-ada-002',
                'chat': 'gpt-3.5-turbo'
            }
        })


class ManualProcessadoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para visualizar manuais processados com conteúdo markdown.
    
    Permite listar e visualizar manuais que foram processados e salvos no banco
    com conteúdo markdown e embeddings para busca semântica.
    """
    queryset = ManualProcessado.objects.all().order_by('-created_at')
    
    def get_serializer_class(self):
        # Serializer simples inline
        from rest_framework import serializers
        
        class ManualProcessadoSerializer(serializers.ModelSerializer):
            total_imagens = serializers.IntegerField(read_only=True)
            tem_embedding = serializers.SerializerMethodField()
            
            def get_tem_embedding(self, obj):
                return bool(obj.embedding)
            
            class Meta:
                model = ManualProcessado
                fields = ['id', 'manual_id', 'titulo', 'url_original', 
                         'conteudo_markdown', 'total_imagens', 'tem_embedding',
                         'created_at', 'updated_at']
        
        return ManualProcessadoSerializer
    
    @extend_schema(
        summary="Listar manuais processados",
        description="Lista todos os manuais que foram processados e salvos no banco de dados."
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @extend_schema(
        summary="Visualizar manual processado",
        description="Visualiza um manual processado específico com todo o conteúdo markdown."
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    
    @extend_schema(
        summary="Buscar manuais por similaridade",
        description="Busca manuais processados usando busca semântica por similaridade.",
        parameters=[
            OpenApiParameter(
                name='pergunta',
                description='Texto da pergunta para busca semântica',
                required=True,
                type=str,
                location=OpenApiParameter.QUERY
            ),
            OpenApiParameter(
                name='limite',
                description='Limite mínimo de similaridade (0.0 a 1.0)',
                required=False,
                type=float,
                location=OpenApiParameter.QUERY
            ),
            OpenApiParameter(
                name='top_k',
                description='Número máximo de resultados',
                required=False,
                type=int,
                location=OpenApiParameter.QUERY
            )
        ]
    )
    @action(detail=False, methods=['get'])
    def buscar_por_similaridade(self, request):
        """Busca manuais processados por similaridade semântica."""
        from .embedding import gerar_embeddings
        
        pergunta = request.query_params.get('pergunta')
        limite = float(request.query_params.get('limite', 0.4))
        top_k = int(request.query_params.get('top_k', 5))
        
        if not pergunta:
            return Response({'erro': 'Parâmetro pergunta é obrigatório'}, status=400)
        
        try:
            pergunta_embedding = gerar_embeddings(pergunta)
            manuais, similaridades = ManualProcessado.objects.buscar_por_similaridade(
                pergunta_embedding, limite, top_k
            )
            
            resultados = []
            for manual, similaridade in zip(manuais, similaridades):
                resultados.append({
                    'id': manual.id,
                    'manual_id': manual.manual_id,
                    'titulo': manual.titulo,
                    'url_original': manual.url_original,
                    'similaridade': similaridade,
                    'total_imagens': manual.total_imagens,
                    'preview_conteudo': manual.conteudo_markdown[:200] + '...' if len(manual.conteudo_markdown) > 200 else manual.conteudo_markdown
                })
            
            return Response({
                'resultados': resultados,
                'total_encontrados': len(resultados),
                'pergunta': pergunta,
                'limite_similaridade': limite
            })
            
        except Exception as e:
            return Response({'erro': str(e)}, status=500)


class ImagemManualViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para servir imagens dos manuais processados.
    
    Permite listar e visualizar imagens que foram extraídas e salvas
    durante o processamento dos manuais.
    """
    queryset = ImagemManual.objects.all().order_by('manual_processado', 'ordem')
    
    def get_serializer_class(self):
        from rest_framework import serializers
        
        class ImagemManualSerializer(serializers.ModelSerializer):
            url_servida = serializers.SerializerMethodField()
            manual_titulo = serializers.CharField(source='manual_processado.titulo', read_only=True)
            
            def get_url_servida(self, obj):
                return obj.get_url_servida()
            
            class Meta:
                model = ImagemManual
                fields = ['id', 'manual_processado', 'manual_titulo', 'url_original', 
                         'nome_arquivo', 'alt_text', 'ordem', 'tamanho_bytes',
                         'url_servida', 'created_at']
        
        return ImagemManualSerializer
    
    @extend_schema(
        summary="Listar imagens dos manuais",
        description="Lista todas as imagens extraídas dos manuais processados."
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @extend_schema(
        summary="Visualizar imagem específica",
        description="Visualiza metadados de uma imagem específica."
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    
    @extend_schema(
        summary="Listar imagens por manual",
        description="Lista todas as imagens de um manual processado específico.",
        parameters=[
            OpenApiParameter(
                name='manual_id',
                description='ID do manual processado',
                required=True,
                type=int,
                location=OpenApiParameter.PATH
            )
        ]
    )
    @action(detail=False, methods=['get'], url_path='manual/(?P<manual_id>[^/.]+)')
    def por_manual(self, request, manual_id=None):
        """Lista imagens de um manual específico."""
        try:
            manual = ManualProcessado.objects.get(id=manual_id)
            imagens = self.queryset.filter(manual_processado=manual)
            serializer = self.get_serializer(imagens, many=True)
            
            return Response({
                'manual': {
                    'id': manual.id,
                    'titulo': manual.titulo,
                    'total_imagens': manual.total_imagens
                },
                'imagens': serializer.data
            })
            
        except ManualProcessado.DoesNotExist:
            return Response({'erro': 'Manual não encontrado'}, status=404)