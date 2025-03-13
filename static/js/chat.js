let utterance = null; // Variável global para manter o objeto da fala

// Abrir o modal
document.getElementById("chat-button").addEventListener("click", () => {
  document.getElementById("chat-modal").style.display = "block";
});

// Fechar o modal
function fecharChat() {
  document.getElementById("chat-modal").style.display = "none";
}

// Função para enviar pergunta
async function enviarPergunta() {
  const pergunta = document.getElementById("chat-input").value.trim();
  if (!pergunta) return;

  // Adiciona a pergunta ao chat
  document.getElementById("chat-body").innerHTML += `<div><b>Você:</b> ${pergunta}</div>`;
  document.getElementById("chat-input").value = "";

  // Realiza o fetch para obter a resposta
  const response = await fetch("api/perguntar/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pergunta }),
  });

  const data = await response.json();
  const resposta = data.resposta;

  // Limpar a resposta anterior e adicionar a nova
  document.getElementById("chat-body").innerHTML += `<div><b>Spart:</b> ${resposta}</div>`;

  // Adicionar o botão de falar a resposta
  document.getElementById("chat-body").innerHTML += `
    <div>
      <button onclick="falarTexto('${resposta}')">🔊 Ouvir Resposta</button>
      <button onclick="pararFala()">❌ Parar Fala</button>
    </div>
  `;
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
