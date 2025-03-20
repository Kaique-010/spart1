from gtts import gTTS
import os
from django.conf import settings
from django.http import JsonResponse
import uuid

def criar_audio(mensagem):
    filename = f"audio_{uuid.uuid4().hex}.mp3"
    audio_path = os.path.join(settings.MEDIA_ROOT, "audio", filename)
    os.makedirs(os.path.dirname(audio_path), exist_ok=True)

    tts = gTTS(mensagem, lang="pt-br")
    tts.save(audio_path)

    audio_url = f"{settings.MEDIA_URL}audio/{filename}"
    return audio_url
