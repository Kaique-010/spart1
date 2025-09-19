from rest_framework import serializers
from .models import Manual, Resposta

class ManualSerializer(serializers.ModelSerializer):
    """Serializer para o modelo Manual."""
    class Meta:
        model = Manual
        fields = ['id', 'title', 'url', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class RespostaSerializer(serializers.ModelSerializer):
    """Serializer para o modelo Resposta."""
    manual = ManualSerializer(read_only=True)
    embedding_status = serializers.SerializerMethodField()
    
    class Meta:
        model = Resposta
        fields = ['id', 'manual', 'content', 'embedding_status', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def get_embedding_status(self, obj):
        return "✅ Sim" if obj.embedding else "❌ Não"

class PerguntaSerializer(serializers.Serializer):
    """Serializer para requisições de perguntas ao agente."""
    pergunta = serializers.CharField(
        max_length=1000,
        help_text="Pergunta a ser enviada ao agente AI",
        style={'placeholder': 'Digite sua pergunta aqui...'}
    )
    
    def validate_pergunta(self, value):
        if not value.strip():
            raise serializers.ValidationError("A pergunta não pode estar vazia.")
        return value.strip()

class RespostaAgentSerializer(serializers.Serializer):
    """Serializer para respostas do agente AI."""
    resposta = serializers.CharField(help_text="Resposta gerada pelo agente AI")
    similaridade = serializers.FloatField(
        help_text="Grau de similaridade com o contexto encontrado (0.0 a 1.0)"
    )
    manual = serializers.URLField(
        required=False, 
        allow_null=True,
        help_text="URL do manual de referência utilizado"
    )
    feedback = serializers.CharField(
        help_text="Feedback sobre como a resposta foi gerada"
    )
    audio_url = serializers.URLField(
        required=False, 
        allow_null=True,
        help_text="URL do arquivo de áudio da resposta (quando disponível)"
    )
    central = serializers.URLField(
        required=False,
        allow_null=True, 
        help_text="Link para central de ajuda (em caso de erro)"
    )
    erro = serializers.CharField(
        required=False,
        allow_null=True,
        help_text="Mensagem de erro (quando aplicável)"
    )

class StreamResponseSerializer(serializers.Serializer):
    """Serializer para respostas em streaming."""
    content = serializers.CharField(
        required=False,
        help_text="Conteúdo parcial da resposta (durante streaming)"
    )
    done = serializers.BooleanField(
        required=False,
        help_text="Indica se o streaming foi finalizado"
    )
    similaridade = serializers.FloatField(
        required=False,
        help_text="Similaridade final (enviada apenas quando done=True)"
    )
    error = serializers.CharField(
        required=False,
        help_text="Mensagem de erro (quando aplicável)"
    )

class BuscarManualSerializer(serializers.Serializer):
    """Serializer para resposta da busca de manual."""
    mensagem = serializers.CharField(help_text="Mensagem de status da operação")
    content = serializers.CharField(help_text="Conteúdo extraído do manual")
    embeddings = serializers.ListField(
        child=serializers.FloatField(),
        help_text="Embeddings gerados para o conteúdo"
    )

class BuscarRespostaSerializer(serializers.Serializer):
    """Serializer para busca de resposta por query."""
    response = serializers.CharField(help_text="Resposta encontrada ou mensagem de erro")