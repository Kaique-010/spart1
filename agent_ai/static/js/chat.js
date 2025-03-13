let utterance = null // Variável global para manter o objeto da fala

// Abrir o modal e enviar saudação automática
document.getElementById('chat-button').addEventListener('click', () => {
  console.log('Botão de chat clicado')
  document.getElementById('chat-modal').style.display = 'block'

  const chatBody = document.getElementById('chat-body')
  console.log('Verificando se há mensagens no chat')

  if (chatBody.innerHTML.trim() === '') {
    console.log('Nenhuma mensagem encontrada. Enviando saudação.')
    const saudacaoDiv = document.createElement('div')
    chatBody.appendChild(saudacaoDiv)

    const typingIndicator = document.createElement('div')
    typingIndicator.id = 'typing-indicator'
    typingIndicator.innerHTML = `<i>Spart está digitando...</i>`
    chatBody.appendChild(typingIndicator)

    escreverTexto(
      saudacaoDiv,
      `Spart: Olá! Como posso te ajudar hoje?`,
      30,
      () => {
        typingIndicator.remove()
        adicionarBotoesFala(saudacaoDiv, 'Olá! Como posso te ajudar hoje?')
        console.log('Saudação enviada')
      }
    )
  }
})

function fecharChat() {
  console.log('Fechando chat')
  document.getElementById('chat-modal').style.display = 'none'
}

async function enviarPergunta() {
  const pergunta = document.getElementById('chat-input').value.trim()
  if (!pergunta) return
  console.log('Pergunta enviada pelo usuário:', pergunta)

  const chatBody = document.getElementById('chat-body')

  const perguntaDiv = document.createElement('div')
  perguntaDiv.innerHTML = `<b>Você:</b> ${pergunta}`
  chatBody.appendChild(perguntaDiv)

  document.getElementById('chat-input').value = ''

  const typingIndicator = document.createElement('div')
  typingIndicator.id = 'typing-indicator'
  typingIndicator.innerHTML = `<i>Spart está digitando...</i>`
  chatBody.appendChild(typingIndicator)

  chatBody.scrollTop = chatBody.scrollHeight

  console.log('Enviando requisição para API')
  const response = await fetch('api/perguntar/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pergunta }),
  })

  typingIndicator.remove()

  const data = await response.json()
  console.log('Resposta recebida da API:', data)
  const { resposta, feedback, sugestao, central, manual } = data

  const respostaDiv = document.createElement('div')
  chatBody.appendChild(respostaDiv)

  escreverTexto(respostaDiv, `Spart: ${resposta}`, 5, () => {
    console.log('Resposta exibida:', resposta)

    if (feedback) {
      const feedbackDiv = document.createElement('div')
      feedbackDiv.style.fontStyle = 'italic'
      feedbackDiv.style.color = '#ccc'
      feedbackDiv.textContent = feedback
      chatBody.appendChild(feedbackDiv)
      console.log('Feedback adicionado:', feedback)
    }

    if (sugestao) {
      const sugestaoDiv = document.createElement('div')
      sugestaoDiv.style.fontStyle = 'italic'
      sugestaoDiv.style.color = '#ccc'
      sugestaoDiv.textContent = sugestao
      chatBody.appendChild(sugestaoDiv)
      console.log('Sugestão adicionada:', sugestao)
    }

    if (central && central.trim() !== '') {
      const centralDiv = document.createElement('div')
      centralDiv.style.fontStyle = 'italic'
      centralDiv.style.color = '#ccc'
      centralDiv.textContent = central
      chatBody.appendChild(centralDiv)
      console.log('Central adicionada:', central)
    }

    if (manual && manual.trim() !== '') {
      const manualDiv = document.createElement('div')
      manualDiv.innerHTML = `<a href="${manual}" target="_blank">📖 Acesse o manual completo aqui</a>`
      manualDiv.style.marginTop = '5px'
      chatBody.appendChild(manualDiv)
      console.log('Link do manual adicionado:', manual)
    }

    adicionarBotoesFala(respostaDiv, resposta)
    chatBody.scrollTop = chatBody.scrollHeight
  })
}

function escreverTexto(element, texto, delay = 30, callback = null) {
  let i = 0
  function escrever() {
    if (i < texto.length) {
      element.textContent += texto.charAt(i)
      i++
      setTimeout(escrever, delay)
    } else if (callback) {
      callback()
    }
  }
  escrever()
}

function falarTexto(texto) {
  if ('speechSynthesis' in window) {
    if (utterance) {
      speechSynthesis.cancel()
    }
    utterance = new SpeechSynthesisUtterance(texto)
    utterance.lang = 'pt-BR'
    utterance.rate = 0.9
    speechSynthesis.speak(utterance)
    console.log('Falando texto:', texto)
  } else {
    console.log('API de síntese de fala não suportada.')
  }
}

function pararFala() {
  if ('speechSynthesis' in window && utterance) {
    speechSynthesis.cancel()
    console.log('Fala interrompida')
  }
}

function adicionarBotoesFala(element, texto) {
  const botaoDiv = document.createElement('div')
  botaoDiv.innerHTML = `
    <button onclick="falarTexto('${texto.replace(
      /'/g,
      "'"
    )}')">🔊 Ouvir</button>
    <button onclick="pararFala()">❌ Parar</button>
  `
  element.appendChild(botaoDiv)
  console.log('Botões de fala adicionados')
}
