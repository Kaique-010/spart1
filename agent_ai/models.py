from django.db import models
import json
import numpy as np
import uuid
from django.utils import timezone
from agent_ai.embedding import gerar_embeddings

class Manual(models.Model):
    title = models.CharField(max_length=255)
    url = models.URLField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        print(f"Salvando manual: {self.title}")
        super().save(*args, **kwargs)
        print(f"Manual {self.title} salvo. Executando o sinal 'post_save'...")







class RespostaManager(models.Manager):
    def buscar_por_similaridade(self, pergunta_embedding, limite_similaridade=0.4, top_k=5):
        """Busca as respostas mais similares usando cálculo vetorial otimizado."""
        respostas = self.exclude(embedding__isnull=True).exclude(embedding__exact='')
        
        if not respostas.exists():
            return [], []
        
        pergunta_embedding = np.array(pergunta_embedding)
        pergunta_norm = pergunta_embedding / np.linalg.norm(pergunta_embedding)
        
        resultados = []
        
        for resposta in respostas:
            try:
                resposta_embedding = np.array(resposta.get_embedding())
                resposta_norm = resposta_embedding / np.linalg.norm(resposta_embedding)
                
                similaridade = np.dot(pergunta_norm, resposta_norm)
                
                if similaridade > limite_similaridade:
                    resultados.append((resposta, float(similaridade)))
            except (ValueError, TypeError, json.JSONDecodeError):
                # Pula embeddings corrompidos
                continue
        
        # Ordena por similaridade decrescente e retorna top_k
        resultados.sort(key=lambda x: x[1], reverse=True)
        
        if resultados:
            respostas_ordenadas, similaridades = zip(*resultados[:top_k])
            return list(respostas_ordenadas), list(similaridades)
        
        return [], []
    
    def buscar_melhor_resposta(self, pergunta_embedding, limite_similaridade=0.4):
        """Retorna apenas a melhor resposta baseada na similaridade."""
        respostas, similaridades = self.buscar_por_similaridade(
            pergunta_embedding, limite_similaridade, top_k=1
        )
        
        if respostas:
            return respostas[0], similaridades[0]
        return None, 0.0


class Resposta(models.Model):
    manual = models.ForeignKey(Manual, on_delete=models.CASCADE, related_name="respostas")
    content = models.TextField()
    embedding = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    objects = RespostaManager()

    def set_embedding(self, embedding):
        """Define o embedding convertendo para JSON."""
        if isinstance(embedding, np.ndarray):
            self.embedding = json.dumps(embedding.tolist())
        elif isinstance(embedding, list):
            self.embedding = json.dumps(embedding)
        else:
            raise ValueError("Embedding deve ser numpy array ou lista")

    def get_embedding(self):
        """Retorna o embedding como numpy array."""
        if not self.embedding:
            return None
        try:
            return json.loads(self.embedding)
        except json.JSONDecodeError:
            return None
    
    def calcular_similaridade(self, outro_embedding):
        """Calcula similaridade cosseno com outro embedding."""
        meu_embedding = np.array(self.get_embedding())
        outro_embedding = np.array(outro_embedding)
        
        if meu_embedding is None or len(meu_embedding) == 0:
            return 0.0
        
        # Normaliza os vetores
        meu_norm = meu_embedding / np.linalg.norm(meu_embedding)
        outro_norm = outro_embedding / np.linalg.norm(outro_embedding)
        
        return float(np.dot(meu_norm, outro_norm))

    def save(self, *args, **kwargs):
        """Gera embeddings automaticamente ao salvar, se necessário."""
        if not self.embedding and self.content:
            embedding_data = gerar_embeddings(self.content)
            self.set_embedding(embedding_data)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Resposta para {self.manual.title} - {self.content[:50]}..."
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Resposta"
        verbose_name_plural = "Respostas"


class Conversa(models.Model):
    """Modelo para armazenar sessões de conversa com o agente AI."""
    session_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    titulo = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    ativa = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Conversa {self.session_id} - {self.titulo or 'Sem título'}"
    
    def get_historico_recente(self, limite=10):
        """Retorna as mensagens mais recentes da conversa."""
        return self.mensagens.order_by('-created_at')[:limite]
    
    def get_contexto_memoria(self, limite=5):
        """Retorna o contexto de memória formatado para o GPT."""
        mensagens_recentes = self.get_historico_recente(limite * 2)  # Pega mais para ter pares pergunta-resposta
        contexto = []
        
        for mensagem in reversed(mensagens_recentes):
            if mensagem.tipo == 'pergunta':
                contexto.append(f"Usuário: {mensagem.conteudo}")
            elif mensagem.tipo == 'resposta':
                contexto.append(f"Assistente: {mensagem.conteudo}")
        
        return "\n".join(contexto[-limite*2:])  # Limita ao número desejado
    
    class Meta:
        ordering = ['-updated_at']
        verbose_name = "Conversa"
        verbose_name_plural = "Conversas"


class Mensagem(models.Model):
    """Modelo para armazenar mensagens individuais de uma conversa."""
    TIPOS_MENSAGEM = [
        ('pergunta', 'Pergunta do Usuário'),
        ('resposta', 'Resposta do Assistente'),
    ]
    
    conversa = models.ForeignKey(Conversa, on_delete=models.CASCADE, related_name='mensagens')
    tipo = models.CharField(max_length=10, choices=TIPOS_MENSAGEM)
    conteudo = models.TextField()
    resposta_relacionada = models.ForeignKey(Resposta, on_delete=models.SET_NULL, null=True, blank=True)
    similaridade = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.get_tipo_display()} - {self.conteudo[:50]}..."
    
    class Meta:
        ordering = ['created_at']
        verbose_name = "Mensagem"
        verbose_name_plural = "Mensagens"
