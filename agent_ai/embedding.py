from sentence_transformers import SentenceTransformer

# Carrega o modelo apenas uma vez para evitar múltiplas cargas desnecessárias
model = SentenceTransformer('paraphrase-MiniLM-L6-v2')

def gerar_embeddings(texto):
    return model.encode([texto])[0]  # Retorna o primeiro resultado, pois passamos uma lista
