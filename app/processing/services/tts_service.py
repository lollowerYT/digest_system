# services/tts_service.py
import uuid
import os
from app.database.models.digest import Digest
from app.database.database import async_session_maker
from app.processing.models.tts import SileroTTS
from app.config import settings

class TTSService:
    def __init__(self, tts_engine: SileroTTS):
        self.tts = tts_engine

    async def generate_audio(self, digest_id: uuid.UUID, digest_text: str) -> str | None:
        audio_dir = settings.AUDIO_STORAGE_PATH
        os.makedirs(audio_dir, exist_ok=True)
        filename = f"digest_{digest_id}.wav"
        filepath = os.path.join(audio_dir, filename)

        try:
            self.tts.create_digest_audio(digest_text, output_file=filepath)
        except Exception as e:
            print(f"TTS failed: {e}")
            return None

        async with async_session_maker() as session:
            digest = await session.get(Digest, digest_id)
            if digest:
                digest.audio_path = filepath
                await session.commit()
        return filepath
    