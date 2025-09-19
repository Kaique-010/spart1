let utterance = null; // Variável global para manter o objeto da fala
let sessionId = null; // Variável para manter o ID da sessão de conversa
let isTyping = false; // Controla se está digitando
let typingIndicator = null; // Referência ao indicador de digitação

// Abrir o modal
document.getElementById("chat-button").addEventListener("click", () => {
  document.getElementById("chat-modal").style.display = "block";
});

// Fechar o modal
function fecharChat() {
  document.getElementById("chat-modal").style.display = "none";
}

// Função para lidar com Enter no input
function handleKeyPress(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    enviarPergunta();
  }
}

// Função para limpar a conversa
function limparConversa() {
  if (confirm('Tem certeza que deseja limpar toda a conversa?')) {
    const chatBody = document.getElementById('chat-body');
    chatBody.innerHTML = `
      <div class="message message-bot">
        <div class="message-label">Spart</div>
        <div class="message-content">
          Olá! 👋 Sou o Spart, seu assistente especializado em ERP Spartacus. Como posso ajudar você hoje?
        </div>
      </div>
    `;
    sessionId = null; // Reset da sessão
  }
}

// Função para scroll automático
function scrollToBottom() {
  const chatBody = document.getElementById('chat-body');
  chatBody.scrollTop = chatBody.scrollHeight;
}

// Função para obter timestamp formatado
function getTimestamp() {
  const now = new Date();
  return now.toLocaleTimeString('pt-BR', { 
    hour: '2-digit', 
    minute: '2-digit' 
  });
}

// Função para mostrar indicador de digitação
function showTypingIndicator() {
  if (typingIndicator) return;
  
  typingIndicator = document.createElement('div');
  typingIndicator.className = 'message message-bot';
  typingIndicator.innerHTML = `
    <div class="message-label">Spart</div>
    <div class="typing-indicator">
      <div class="typing-dots">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
      </div>
    </div>
  `;
  
  document.getElementById('chat-body').appendChild(typingIndicator);
  scrollToBottom();
}

// Função para esconder indicador de digitação
function hideTypingIndicator() {
  if (typingIndicator) {
    typingIndicator.remove();
    typingIndicator = null;
  }
}

// Função para adicionar mensagem do usuário
function addUserMessage(message) {
  const chatBody = document.getElementById('chat-body');
  const messageDiv = document.createElement('div');
  messageDiv.className = 'message message-user';
  messageDiv.innerHTML = `
    <div class="message-label">Você</div>
    <div class="message-content">${message}</div>
    <div class="message-timestamp">${getTimestamp()}</div>
  `;
  chatBody.appendChild(messageDiv);
  scrollToBottom();
}

// Função para adicionar mensagem do bot
function addBotMessage(message, showActions = true) {
  const chatBody = document.getElementById('chat-body');
  const messageDiv = document.createElement('div');
  messageDiv.className = 'message message-bot';
  
  let actionsHtml = '';
  if (showActions) {
    actionsHtml = `
      <div class="message-actions">
        <button class="action-button" onclick="falarTexto('${message.replace(/'/g, "\\'")}')">🔊 Ouvir</button>
        <button class="action-button" onclick="pararFala()">⏹️ Parar</button>
      </div>
    `;
  }
  
  messageDiv.innerHTML = `
    <div class="message-label">Spart</div>
    <div class="message-content">${message}</div>
    <div class="message-timestamp">${getTimestamp()}</div>
    ${actionsHtml}
  `;
  
  chatBody.appendChild(messageDiv);
  scrollToBottom();
  return messageDiv;
}

// Função para enviar pergunta com streaming
async function enviarPergunta() {
  const pergunta = document.getElementById("chat-input").value;
  if (!pergunta.trim() || isTyping) return;

  // Marcar como digitando e limpar o campo
   isTyping = true;
   document.getElementById("chat-input").value = "";
   document.getElementById("send-button").disabled = true;

  // Adicionar mensagem do usuário
  addUserMessage(pergunta);

  // Mostrar indicador de digitação
  showTypingIndicator();

  // Preparar o corpo da requisição
  const body = {
    pergunta: pergunta
  };

  // Adicionar session_id se existir
  if (sessionId) {
    body.session_id = sessionId;
  }

  try {
    const response = await fetch("api/perguntar-stream/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    // Esconder indicador de digitação
    hideTypingIndicator();

    // Criar elemento para a resposta em streaming
    const chatBody = document.getElementById("chat-body");
    const respostaDiv = document.createElement("div");
    respostaDiv.className = 'message message-bot';
    respostaDiv.innerHTML = `
      <div class="message-label">Spart</div>
      <div class="message-content"></div>
      <div class="message-timestamp">${getTimestamp()}</div>
    `;
    chatBody.appendChild(respostaDiv);
    
    const contentDiv = respostaDiv.querySelector('.message-content');

    // Ler o stream
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let respostaCompleta = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      const lines = chunk.split("\n");

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const data = line.slice(6);
          if (data === "[DONE]") {
            break;
          }
          try {
            const parsed = JSON.parse(data);
            if (parsed.content) {
              respostaCompleta += parsed.content;
              contentDiv.innerHTML = respostaCompleta;
              scrollToBottom();
            }
            if (parsed.session_id) {
              sessionId = parsed.session_id;
            }
          } catch (e) {
            // Ignorar linhas que não são JSON válido
          }
        }
      }
    }

    // Adicionar botões de áudio após a resposta completa
    const actionsDiv = document.createElement("div");
    actionsDiv.className = 'message-actions';
    actionsDiv.innerHTML = `
      <button class="action-button" onclick="falarTexto('${respostaCompleta.replace(/'/g, "\\'")}')">🔊 Ouvir</button>
      <button class="action-button" onclick="pararFala()">⏹️ Parar</button>
    `;
    respostaDiv.appendChild(actionsDiv);

  } catch (error) {
    console.error("Erro ao enviar pergunta:", error);
    hideTypingIndicator();
    addBotMessage(`❌ Erro: ${error.message}`, false);
  } finally {
     // Reabilitar interface
     isTyping = false;
     document.getElementById("send-button").disabled = false;
     document.getElementById("chat-input").focus();
   }
}

// Função para falar a resposta
function falarTexto(texto) {
  if ('speechSynthesis' in window) {
    // Se já houver alguma fala em andamento, cancela
    if (utterance) {
      speechSynthesis.cancel(); // Cancela a fala anterior
    }

    // Cria o novo objeto de fala
    utterance = new SpeechSynthesisUtterance(texto);
    utterance.lang = 'pt-BR';
    utterance.rate = 0.9; // Velocidade da fala
    speechSynthesis.speak(utterance);
  } else {
    console.log("Seu navegador não suporta a API de síntese de fala.");
  }
}

// Função para parar a fala
function pararFala() {
  if ('speechSynthesis' in window && utterance) {
    speechSynthesis.cancel(); // Cancela a fala em andamento
  }
}
