from django.db import models
import json
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







class Resposta(models.Model):
    manual = models.ForeignKey(Manual, on_delete=models.CASCADE, related_name="respostas")
    content = models.TextField()
    embedding = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def set_embedding(self, embedding):
        self.embedding = json.dumps(embedding.tolist())

    def get_embedding(self):
        """Retorna o embedding como lista"""
        return json.loads(self.embedding) if self.embedding else None

    def save(self, *args, **kwargs):
        """Gera embeddings automaticamente ao salvar, se necessário"""
        if not self.embedding and self.content:
            self.embedding = json.dumps(gerar_embeddings(self.content))
        super().save(*args, **kwargs)
