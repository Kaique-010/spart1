from django.contrib import admin
from django.contrib import messages
from .models import Manual, Resposta
from .embedding import gerar_embeddings
import json

@admin.register(Manual)
class ManualAdmin(admin.ModelAdmin):
    list_display = ["title", "url", "created_at"]
    search_fields = ["title", "url"]

@admin.register(Resposta)
class RespostaAdmin(admin.ModelAdmin):
    list_display = ["manual", "content", "embedding_status"]
    search_fields = ["content"]
    actions = ["gerar_embeddings_action"]

    def embedding_status(self, obj):
        return "✅ Sim" if obj.embedding else "❌ Não"
    embedding_status.short_description = "Embeddings?"

    @admin.action(description="Gerar embeddings para respostas selecionadas")
    def gerar_embeddings_action(self, request, queryset):
        count = 0
        for resposta in queryset:
            if not resposta.embedding:  # Só gerar se não existir
                resposta.set_embedding(gerar_embeddings(resposta.content))
                resposta.save(update_fields=["embedding"])  # Evita chamar `save()` completo
                count += 1
        self.message_user(request, f"{count} embeddings gerados com sucesso.", messages.SUCCESS)
