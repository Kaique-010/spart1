from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import StreamingHttpResponse
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.openapi import AutoSchema
from .models import Manual, Resposta
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
                # Reutiliza a função existente
                response = perguntar_spart(request)
                if hasattr(response, 'content'):
                    data = json.loads(response.content)
                    return Response(data, status=response.status_code)
                return response
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