import re
import torch
import soundfile as sf
import numpy as np
import os
import logging

logger = logging.getLogger(__name__)

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

    def _clean_text(self, text: str) -> str:
        """Очистка текста от символов, которые Silero не может обработать."""
        # Удаляем эмодзи и спецсимволы, оставляем буквы, цифры, пробелы, . , ! ? - ( ) " '
        text = re.sub(r'[^\w\s.,!?\-()\"\']', ' ', text)
        # Заменяем множественные точки на одну
        text = re.sub(r'\.{2,}', '.', text)
        # Убираем точки в начале и конце
        text = text.strip('.')
        # Заменяем множественные пробелы одним
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Если строка состоит только из цифр, точек и пробелов – удаляем (это бесполезные фрагменты)
        if re.fullmatch(r'[\d\.\s]+', text):
            return ""
        
        # Ограничиваем длину (Silero имеет внутренний лимит)
        if len(text) > 500:
            text = text[:500]
        return text

    def synthesize(self, text, output_file=None):
        clean_text = self._clean_text(text)
        if not clean_text or len(clean_text) < 2:
            logger.warning(f"Текст после очистки слишком короткий или пуст: '{text[:50]}...'")
            return np.array([])
        try:
            audio = self.model.apply_tts(text=clean_text,
                                          speaker=self.speaker,
                                          sample_rate=self.sample_rate,
                                          put_accent=True,
                                          put_yo=True)
            audio_np = audio.numpy()
            if output_file:
                sf.write(output_file, audio_np, self.sample_rate)
            return audio_np
        except Exception as e:
            logger.error(f"Ошибка синтеза для текста: {clean_text[:100]}...")
            logger.exception(e)
            raise

    def create_digest_audio(self, digest_text, output_file="digest.wav"):
        try:
            # Разбиваем на предложения
            sentences = re.split(r'(?<=[.!?])\s+', digest_text)
            sentences = [s.strip() for s in sentences if s.strip()]
            logger.info(f"Синтез аудио: {len(sentences)} предложений")
            audio_parts = []
            for i, sent in enumerate(sentences):
                if not sent:
                    continue
                logger.debug(f"Предложение {i+1}/{len(sentences)}: {sent[:50]}...")
                try:
                    audio = self.synthesize(sent)
                    if audio.size > 0:
                        audio_parts.append(audio)
                    else:
                        logger.warning(f"Предложение {i+1} не дало аудио")
                except Exception as e:
                    logger.error(f"Ошибка синтеза предложения {i+1}: '{sent[:100]}...'")
                    logger.exception(e)
                    continue
            if audio_parts:
                combined = np.concatenate(audio_parts)
                sf.write(output_file, combined, self.sample_rate)
                logger.info(f"Аудио сохранено: {output_file}")
                return combined
            else:
                logger.error("Не удалось синтезировать ни одного предложения")
                return None
        except Exception as e:
            logger.error("Внутренняя ошибка Silero TTS:")
            logger.exception(e)
            raise