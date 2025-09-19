from gtts import gTTS
import os
from django.conf import settings
from django.http import JsonResponse, StreamingHttpResponse
import uuid
import threading
import time
from concurrent.futures import ThreadPoolExecutor
import logging

logger = logging.getLogger(__name__)

def criar_audio(mensagem, lang="pt-br", slow=False):
    """Cria arquivo de áudio a partir de texto usando gTTS."""
    try:
        filename = f"audio_{uuid.uuid4().hex}.mp3"
        audio_path = os.path.join(settings.MEDIA_ROOT, "audio", filename)
        os.makedirs(os.path.dirname(audio_path), exist_ok=True)

        tts = gTTS(text=mensagem, lang=lang, slow=slow)
        tts.save(audio_path)

        audio_url = f"{settings.MEDIA_URL}audio/{filename}"
        return audio_url
    except Exception as e:
        logger.error(f"Erro ao criar áudio: {str(e)}")
        return None


def criar_audio_async(mensagem, callback=None, lang="pt-br", slow=False):
    """Cria áudio de forma assíncrona para não bloquear a resposta."""
    def _criar_audio_thread():
        try:
            audio_url = criar_audio(mensagem, lang, slow)
            if callback and audio_url:
                callback(audio_url)
            return audio_url
        except Exception as e:
            logger.error(f"Erro ao criar áudio assíncrono: {str(e)}")
            if callback:
                callback(None)
            return None
    
    thread = threading.Thread(target=_criar_audio_thread)
    thread.daemon = True
    thread.start()
    return thread


def criar_audio_streaming(texto_stream, lang="pt-br"):
    """Cria áudio a partir de um stream de texto em tempo real."""
    def generate_audio():
        buffer_texto = ""
        sentence_endings = ['.', '!', '?', '\n']
        
        for chunk in texto_stream:
            buffer_texto += chunk
            
            # Quando encontrar fim de frase, gera áudio
            for ending in sentence_endings:
                if ending in buffer_texto:
                    sentences = buffer_texto.split(ending)
                    for sentence in sentences[:-1]:  # Todas exceto a última
                        if sentence.strip():
                            try:
                                audio_url = criar_audio(sentence.strip(), lang)
                                if audio_url:
                                    yield f"data: {{\"audio_url\": \"{audio_url}\"}}\n\n"
                            except Exception as e:
                                logger.error(f"Erro ao gerar áudio para frase: {str(e)}")
                    
                    buffer_texto = sentences[-1]  # Mantém o resto
                    break
        
        # Processa texto restante
        if buffer_texto.strip():
            try:
                audio_url = criar_audio(buffer_texto.strip(), lang)
                if audio_url:
                    yield f"data: {{\"audio_url\": \"{audio_url}\"}}\n\n"
            except Exception as e:
                logger.error(f"Erro ao gerar áudio final: {str(e)}")
    
    return generate_audio()


def limpar_audios_antigos(dias=7):
    """Remove arquivos de áudio mais antigos que X dias."""
    try:
        audio_dir = os.path.join(settings.MEDIA_ROOT, "audio")
        if not os.path.exists(audio_dir):
            return 0
        
        count = 0
        cutoff_time = time.time() - (dias * 24 * 60 * 60)
        
        for filename in os.listdir(audio_dir):
            if filename.startswith("audio_") and filename.endswith(".mp3"):
                file_path = os.path.join(audio_dir, filename)
                if os.path.getctime(file_path) < cutoff_time:
                    try:
                        os.remove(file_path)
                        count += 1
                    except OSError as e:
                        logger.error(f"Erro ao remover {file_path}: {str(e)}")
        
        logger.info(f"Removidos {count} arquivos de áudio antigos")
        return count
    except Exception as e:
        logger.error(f"Erro na limpeza de áudios: {str(e)}")
        return 0


def validar_texto_audio(texto, max_chars=5000):
    """Valida se o texto é adequado para conversão em áudio."""
    if not texto or not texto.strip():
        return False, "Texto vazio"
    
    if len(texto) > max_chars:
        return False, f"Texto muito longo (máximo {max_chars} caracteres)"
    
    # Remove caracteres especiais problemáticos
    texto_limpo = ''.join(char for char in texto if char.isprintable() or char.isspace())
    
    return True, texto_limpo
