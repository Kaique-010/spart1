from sentence_transformers import SentenceTransformer


model = SentenceTransformer('paraphrase-MiniLM-L6-v2')

def gerar_embeddings(texto):
    return model.encode([texto])[0]  
