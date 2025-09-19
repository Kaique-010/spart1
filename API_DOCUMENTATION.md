# 📚 Spartacus AI Agent API - Documentação

## 🚀 Visão Geral

A **Spartacus AI Agent API** é um sistema de assistente virtual inteligente que combina busca vetorial, processamento de linguagem natural e geração de áudio para fornecer respostas contextualizadas sobre o sistema Spartacus.

## 🔗 Endpoints Principais

### 🌐 Documentação Interativa
- **Swagger UI**: `http://localhost:8000/api/docs/`
- **ReDoc**: `http://localhost:8000/api/redoc/`
- **Schema OpenAPI**: `http://localhost:8000/api/schema/`

### 🤖 Agente AI

#### POST `/api/agente/perguntar/`
**Pergunta ao Agente (Versão Padrão)**

```json
{
  "pergunta": "Como fazer backup no sistema Spartacus?"
}
```

**Resposta:**
```json
{
  "resposta": "Para fazer backup no sistema Spartacus, acesse...",
  "similaridade": 0.85,
  "manual": "https://spartacus.movidesk.com/kb/article/123",
  "feedback": "Resposta gerada com IA baseada no conhecimento do sistema.",
  "audio_url": "/media/audio/audio_abc123.mp3"
}
```

#### POST `/api/agente/perguntar_stream/`
**Pergunta ao Agente (Versão Streaming)**

Retorna respostas em tempo real usando Server-Sent Events (SSE).

```bash
curl -X POST http://localhost:8000/api/agente/perguntar_stream/ \
  -H "Content-Type: application/json" \
  -d '{"pergunta": "Como configurar usuários?"}'
```

**Resposta (Stream):**
```
data: {"content": "Para configurar"}
data: {"content": " usuários no"}
data: {"content": " sistema..."}
data: {"done": true, "similaridade": 0.85}
```

#### GET `/api/agente/status/`
**Status da API**

Retorna informações sobre o status e recursos disponíveis.

### 📚 Manuais

#### GET `/api/manuais/`
**Listar Manuais**

Retorna lista paginada de manuais cadastrados.

#### GET `/api/manuais/{id}/`
**Detalhes do Manual**

Retorna detalhes de um manual específico.

#### POST `/api/manuais/{id}/buscar_conteudo/`
**Processar Manual**

Extrai conteúdo de um manual e gera embeddings.

#### GET `/api/manuais/{id}/resposta/{query}/`
**Buscar Resposta**

Busca resposta específica usando uma query de texto.

### 💬 Respostas

#### GET `/api/respostas/`
**Listar Respostas**

Retorna lista paginada de respostas armazenadas.

#### GET `/api/respostas/{id}/`
**Detalhes da Resposta**

Retorna detalhes de uma resposta específica.

## 🛠️ Tecnologias Utilizadas

### 🧠 Modelos de IA
- **Embeddings**: `text-embedding-ada-002` (OpenAI)
- **Chat**: `gpt-3.5-turbo` (OpenAI)
- **Áudio**: `gTTS` (Google Text-to-Speech)

### 🔧 Framework
- **Backend**: Django + Django REST Framework
- **Documentação**: drf-spectacular (OpenAPI 3.0)
- **Banco de Dados**: SQLite (desenvolvimento) / PostgreSQL (produção)

## 🚀 Como Usar

### 1. Instalação
```bash
# Clone o repositório
git clone <repository-url>
cd spart1

# Ative o ambiente virtual
.\venv\Scripts\Activate.ps1

# Instale as dependências
pip install -r requirements.txt

# Configure as variáveis de ambiente
cp .env.example .env
# Edite o .env com suas chaves da OpenAI
```

### 2. Configuração
```bash
# Execute as migrações
python manage.py migrate

# Crie um superusuário (opcional)
python manage.py createsuperuser

# Inicie o servidor
python manage.py runserver
```

### 3. Teste da API
```bash
# Teste básico
curl -X POST http://localhost:8000/api/agente/perguntar/ \
  -H "Content-Type: application/json" \
  -d '{"pergunta": "Como funciona o sistema Spartacus?"}'

# Verificar status
curl http://localhost:8000/api/agente/status/
```

## 📖 Exemplos de Uso

### JavaScript (Frontend)
```javascript
// Pergunta simples
const response = await fetch('/api/agente/perguntar/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    pergunta: 'Como fazer backup dos dados?'
  })
});

const data = await response.json();
console.log(data.resposta);

// Streaming
const eventSource = new EventSource('/api/agente/perguntar_stream/');
eventSource.onmessage = function(event) {
  const data = JSON.parse(event.data);
  if (data.content) {
    console.log(data.content); // Conteúdo parcial
  } else if (data.done) {
    console.log('Finalizado:', data.similaridade);
    eventSource.close();
  }
};
```

### Python (Cliente)
```python
import requests

# Pergunta ao agente
response = requests.post(
    'http://localhost:8000/api/agente/perguntar/',
    json={'pergunta': 'Como configurar relatórios?'}
)

data = response.json()
print(f"Resposta: {data['resposta']}")
print(f"Similaridade: {data['similaridade']}")

if data.get('audio_url'):
    print(f"Áudio disponível: {data['audio_url']}")
```

## 🔒 Segurança

- **CORS**: Configurado para desenvolvimento
- **CSRF**: Desabilitado para endpoints da API
- **Rate Limiting**: Recomendado para produção
- **Autenticação**: Atualmente pública (configurar para produção)

## 📊 Monitoramento

### Métricas Disponíveis
- Status da API: `/api/agente/status/`
- Logs do Django: Console/arquivo
- Métricas de uso: Implementar com Django Debug Toolbar

## 🚀 Deploy em Produção

### Variáveis de Ambiente Necessárias
```bash
OPENAI_API_KEY=sk-...
DJANGO_SECRET_KEY=...
DATABASE_URL=postgresql://...
DEBUG=False
ALLOWED_HOSTS=api.spartacus.com
```

### Docker
```bash
# Build da imagem
docker build -t spartacus-api .

# Executar com docker-compose
docker-compose up -d
```

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature
3. Commit suas mudanças
4. Push para a branch
5. Abra um Pull Request

## 📞 Suporte

- **Email**: suporte@spartacus.com.br
- **Central de Ajuda**: https://spartacus.movidesk.com/kb/
- **Documentação**: http://localhost:8000/api/docs/

---

**Spartacus AI Agent API v1.0.0** - Sistema de assistente virtual inteligente