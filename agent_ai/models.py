from django.db import models
import json
import numpy as np
import uuid
from django.utils import timezone
from agent_ai.embedding import gerar_embeddings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

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


class ManualProcessadoManager(models.Manager):
    def buscar_por_similaridade(self, pergunta_embedding, limite_similaridade=0.4, top_k=5):
        """Busca manuais por similaridade semântica."""
        resultados = []
        
        for manual in self.filter(embedding__isnull=False).exclude(embedding=''):
            try:
                manual_embedding = manual.get_embedding()
                if not manual_embedding:
                    continue
                
                # Calcula similaridade cosseno
                similaridade = manual.calcular_similaridade(pergunta_embedding)
                
                if similaridade > limite_similaridade:
                    resultados.append((manual, float(similaridade)))
            except (ValueError, TypeError, json.JSONDecodeError):
                # Pula embeddings corrompidos
                continue
        
        # Ordena por similaridade decrescente e retorna top_k
        resultados.sort(key=lambda x: x[1], reverse=True)
        
        if resultados:
            manuais_ordenados, similaridades = zip(*resultados[:top_k])
            return list(manuais_ordenados), list(similaridades)
        
        return [], []
    
    def buscar_melhor_manual(self, pergunta_embedding, limite_similaridade=0.4):
        """Retorna apenas o melhor manual baseado na similaridade."""
        manuais, similaridades = self.buscar_por_similaridade(
            pergunta_embedding, limite_similaridade, top_k=1
        )
        
        if manuais:
            return manuais[0], similaridades[0]
        return None, 0.0


class ManualProcessado(models.Model):
    """Modelo para armazenar manuais processados com conteúdo markdown."""
    manual_id = models.IntegerField(unique=True, help_text="ID original do manual")
    titulo = models.CharField(max_length=255)
    url_original = models.URLField()
    conteudo_markdown = models.TextField(help_text="Conteúdo do manual em formato markdown")
    conteudo_html_original = models.TextField(blank=True, help_text="HTML original para referência")
    embedding = models.TextField(blank=True, null=True, help_text="Embedding do conteúdo para busca semântica")
    total_imagens = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = ManualProcessadoManager()
    
    def set_embedding(self, embedding):
        """Armazena o embedding como JSON string."""
        if embedding is not None:
            self.embedding = json.dumps(embedding.tolist() if hasattr(embedding, 'tolist') else embedding)
    
    def get_embedding(self):
        """Recupera o embedding como numpy array."""
        if self.embedding:
            return json.loads(self.embedding)
        return None
    
    def gerar_embedding(self):
        """Gera embedding para o conteúdo markdown."""
        if self.conteudo_markdown:
            embedding = gerar_embeddings(self.conteudo_markdown)
            self.set_embedding(embedding)
            return embedding
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
        # Gerar embedding automaticamente se não existir
        if not self.embedding and self.conteudo_markdown:
            self.gerar_embedding()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Manual {self.manual_id}: {self.titulo}"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Manual Processado"
        verbose_name_plural = "Manuais Processados"


class ImagemManual(models.Model):
    """Modelo para armazenar imagens dos manuais."""
    manual_processado = models.ForeignKey(ManualProcessado, on_delete=models.CASCADE, related_name='imagens')
    url_original = models.URLField(help_text="URL original da imagem")
    arquivo_imagem = models.ImageField(upload_to='manuais/imagens/', help_text="Arquivo da imagem salvo localmente")
    nome_arquivo = models.CharField(max_length=255, help_text="Nome do arquivo gerado")
    alt_text = models.CharField(max_length=255, default="Imagem", help_text="Texto alternativo da imagem")
    ordem = models.IntegerField(help_text="Ordem da imagem no manual")
    hash_conteudo = models.CharField(max_length=64, help_text="Hash do conteúdo da imagem para evitar duplicatas")
    tamanho_bytes = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def get_url_servida(self):
        """Retorna a URL para servir a imagem via Django."""
        if self.arquivo_imagem:
            return self.arquivo_imagem.url
        return None
    
    def __str__(self):
        return f"Imagem {self.ordem} - {self.nome_arquivo}"
    
    class Meta:
        ordering = ['manual_processado', 'ordem']
        unique_together = ['manual_processado', 'ordem']
        verbose_name = "Imagem do Manual"
        verbose_name_plural = "Imagens dos Manuais"
