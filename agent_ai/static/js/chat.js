document.getElementById('chat-button').addEventListener('click', () => {
  document.getElementById('chat-modal').style.display = 'block'
})

function fecharChat() {
  document.getElementById('chat-modal').style.display = 'none'
}

async function enviarPergunta() {
  const pergunta = document.getElementById('chat-input').value.trim()
  if (!pergunta) return

  const chatBody = document.getElementById('chat-body')

  // Adicionar mensagem do usuário
  const perguntaDiv = document.createElement('div')
  perguntaDiv.classList.add('chat-message', 'user-message')
  perguntaDiv.innerHTML = `<b>Você:</b> ${pergunta}`
  chatBody.appendChild(perguntaDiv)
  document.getElementById('chat-input').value = ''

  // Indicador de digitação
  const typingIndicator = document.createElement('div')
  typingIndicator.innerHTML = `<i>Spart está Pensando...</i>`
  chatBody.appendChild(typingIndicator)
  chatBody.scrollTop = chatBody.scrollHeight

  // Enviar requisição para a API
  const response = await fetch('api/perguntar/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pergunta }),
  })

  typingIndicator.remove()

  const data = await response.json()
  console.log('Resposta recebida da API:', data)
  const { resposta, audio_url, feedback, sugestao, central, manual } = data

  // Adicionar resposta do bot com função de escrita
  const respostaDiv = document.createElement('div')
  respostaDiv.classList.add('chat-message', 'bot-message')
  respostaDiv.innerHTML = `<b>Spart:</b> ${resposta}`
  chatBody.appendChild(respostaDiv)

  // Chamar a função de escreverTexto para a resposta
  escreverTexto(respostaDiv, resposta)

  // Adicionar player de áudio, se houver, e iniciar automaticamente
  if (audio_url && audio_url.trim() !== '') {
    const audioDiv = document.createElement('div')
    audioDiv.classList.add('audio-message')

    const audioElement = document.createElement('audio')
    audioElement.controls = true
    audioElement.autoplay = true
    audioElement.playbackRate = 1.5 // Definindo a velocidade para 1.5x
    const source = document.createElement('source')
    source.src = audio_url
    source.type = 'audio/mpeg'
    audioElement.appendChild(source)

    audioDiv.appendChild(audioElement)
    chatBody.appendChild(audioDiv)
  }

  // Exibir mensagens de feedback, sugestão, central, manual
  if (feedback) {
    const feedbackDiv = document.createElement('div')
    feedbackDiv.style.fontStyle = 'italic'
    feedbackDiv.style.color = '#ccc'
    feedbackDiv.textContent = feedback
    chatBody.appendChild(feedbackDiv)
  }

  if (sugestao) {
    const sugestaoDiv = document.createElement('div')
    sugestaoDiv.style.fontStyle = 'italic'
    sugestaoDiv.style.color = '#ccc'
    sugestaoDiv.textContent = sugestao
    chatBody.appendChild(sugestaoDiv)
  }

  if (central && central.trim() !== '') {
    const centralDiv = document.createElement('div')
    centralDiv.style.fontStyle = 'italic'
    centralDiv.style.color = '#ccc'
    centralDiv.textContent = central
    chatBody.appendChild(centralDiv)
  }

  if (manual && manual.trim() !== '') {
    const manualDiv = document.createElement('div')
    manualDiv.innerHTML = ` 
      <a href="${manual}" target="_blank">
        📖 Acesse o manual completo aqui
      </a>
    `
    manualDiv.style.marginTop = '5px'
    chatBody.appendChild(manualDiv)
  }

  chatBody.scrollTop = chatBody.scrollHeight
}

const TYPING_SPEED = 1.5

function escreverTexto(
  element,
  texto,
  delay = 15,
  speed = TYPING_SPEED,
  callback = null
) {
  let i = 0
  function escrever() {
    if (i < texto.length) {
      element.textContent += texto.charAt(i)
      i++
      setTimeout(escrever, speed * 10) // Ajuste na lógica para chamar o próximo caractere com a velocidade
    } else if (callback) {
      callback()
    }
  }
  escrever()
}
