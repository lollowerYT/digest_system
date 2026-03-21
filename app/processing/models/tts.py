# models/tts.py
import torch
import soundfile as sf
import numpy as np
import os

class SileroTTS:
    def __init__(self, speaker='xenia', sample_rate=24000):
        self.speaker = speaker
        self.sample_rate = sample_rate
        self.device = 'cpu'
        print("Загрузка Silero TTS...")
        self.model, _ = torch.hub.load(repo_or_dir='snakers4/silero-models',
                                        model='silero_tts',
                                        language='ru',
                                        speaker='v4_ru')
        self.model.to(self.device)
        print("✅ Silero загружен")

    def synthesize(self, text, output_file=None):
        audio = self.model.apply_tts(text=text,
                                      speaker=self.speaker,
                                      sample_rate=self.sample_rate,
                                      put_accent=True,
                                      put_yo=True)
        audio_np = audio.numpy()
        if output_file:
            sf.write(output_file, audio_np, self.sample_rate)
        return audio_np

    def create_digest_audio(self, digest_text, output_file="digest.wav"):
        try:
            sentences = [s.strip() + '.' for s in digest_text.split('.') if s.strip()]
            audio_parts = []
            for sent in sentences:
                if sent:
                    audio = self.synthesize(sent)
                    audio_parts.append(audio)
            if audio_parts:
                combined = np.concatenate(audio_parts)
                sf.write(output_file, combined, self.sample_rate)
                return combined
            return None
        except Exception as e:
            print(f"❌ Внутренняя ошибка Silero TTS: {e}")
            raise