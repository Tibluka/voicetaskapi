import subprocess
import tempfile
import os
from openai import OpenAI
from decouple import config
from services.gpt import ask_gpt

API_KEY = config("API_KEY_OPENAI")

def convert_caf_to_wav(input_path):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmpfile:
        output_path = tmpfile.name

    cmd = ['ffmpeg', '-i', input_path, output_path, '-y']  # -y sobrescreve se existir
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

    return output_path

def transcribe(audio_path):
    try:
        client = OpenAI(api_key=API_KEY)

        # Converte para wav
        wav_path = convert_caf_to_wav(audio_path)

        with open(wav_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="gpt-4o-transcribe",
                file=audio_file,
                language="pt"
            )

        os.remove(wav_path)
        
        response = ask_gpt(transcription.text)

        return {
            "gpt": response,
            "prompt": transcription.text
        }

    except Exception as e:
        print("Erro na transcrição:", e)
        return None