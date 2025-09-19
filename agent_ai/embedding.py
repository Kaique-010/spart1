from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def gerar_embeddings(texto):
    response = client.embeddings.create(
        model="text-embedding-ada-002",
        input=texto
    )
    return response.data[0].embedding
    
