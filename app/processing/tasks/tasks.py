import asyncio
import uuid
import json
import logging
import numpy as np
from datetime import datetime
from typing import Dict, Any, List
from celery import chain
from app.processing.tasks.celery_app import celery_app
from app.processing.services.telegram_collector import TelegramCollector
from app.processing.services.embedding_service import EmbeddingService
from app.processing.services.clustering_service import ClusteringService
from app.processing.services.summarization_service import SummarizationService
from app.processing.services.tts_service import TTSService
from app.processing.models.qwen_embedder import QwenEmbedder
from app.processing.models.summarizer import SaigaSummarizer
from app.processing.models.tts import SileroTTS
from app.config import settings
from app.database.models.digest import Digest
from app.database.models.query_history import QueryHistory
from app.database.models.channel import TelegramChannel
from app.database.models.token_transaction import TokenTransaction
from app.database.models.news import News
from app.database.models.user import User
from app.database.models.cluster import Cluster
from app.database.models.embedding import Embedding
from app.database.database import async_session_maker
from sqlalchemy import select
from app.processing.utils.filtering import set_embedder, get_ad_embedding, filter_ad_by_embeddings

logger = logging.getLogger(__name__)

# Инициализация сервисов (один раз при старте воркера)
collector = TelegramCollector(
    api_id=settings.API_ID,
    api_hash=settings.API_HASH,
    phone=settings.PHONE_NUMBER
)
embedder = QwenEmbedder(
    model_name="Qwen/Qwen3-Embedding-4B",
    device="cuda",  # или "cpu" если нет GPU
    embedding_dim=4096
)
set_embedder(embedder)
get_ad_embedding()  # прогреваем кэш

summarizer = SaigaSummarizer(
    model_name=settings.SAIGA_MODEL,
    host=settings.OLLAMA_HOST
)
tts_engine = SileroTTS(speaker='xenia')

embedding_service = EmbeddingService(embedder)
clustering_service = ClusteringService()
summarization_service = SummarizationService(summarizer)
tts_service = TTSService(tts_engine)


@celery_app.task(bind=True)
def generate_digest(self, user_id: str, digest_id: str, request_data: Dict[str, Any]):
    loop = asyncio.get_event_loop()
    try:
        result = loop.run_until_complete(
            _generate_digest_async(
                uuid.UUID(user_id),
                uuid.UUID(digest_id),
                request_data
            )
        )
        return result
    except Exception as e:
        logger.exception("Error in generate_digest")
        return {"status": "error", "error": str(e)}


async def _generate_digest_async(
    user_id: uuid.UUID,
    digest_id: uuid.UUID,
    request_data: Dict[str, Any]
):
    # 1. Получаем каналы из БД
    async with async_session_maker() as session:
        stmt = select(TelegramChannel).where(
            TelegramChannel.username.in_(request_data['channels'])   # username = ссылка
        )
        result = await session.execute(stmt)
        channels = result.scalars().all()
        if not channels:
            logger.info(f"No active channels for digest {digest_id}")
            return {"digest_id": str(digest_id), "status": "no_active_channels"}

    # 2. Сбор новостей
    date_from = datetime.fromisoformat(request_data['date_from'])
    news_items = await collector.collect_news_for_channels(channels, date_from)
    if not news_items:
        return {"digest_id": str(digest_id), "status": "no_news"}

    news_ids = [n.id for n in news_items]
    texts = [n.text for n in news_items]

    # 3. Загружаем существующие эмбеддинги
    async with async_session_maker() as session:
        stmt = select(Embedding.news_id, Embedding.vector).where(Embedding.news_id.in_(news_ids))
        rows = await session.execute(stmt)
        existing_embeddings = {row.news_id: np.array(row.vector) for row in rows}

    # 4. Генерируем эмбеддинги для новых новостей
    missing_indices = [i for i, nid in enumerate(news_ids) if nid not in existing_embeddings]
    if missing_indices:
        missing_texts = [texts[i] for i in missing_indices]
        missing_ids = [news_ids[i] for i in missing_indices]
        logger.info(f"Генерация эмбеддингов для {len(missing_ids)} новых новостей")
        new_vectors = embedder.get_batch_embeddings(missing_texts)
        await embedding_service.save_embeddings(missing_ids, new_vectors)
        for nid, vec in zip(missing_ids, new_vectors):
            existing_embeddings[nid] = vec

    # 5. Собираем матрицу эмбеддингов в порядке news_ids
    vectors = np.array([existing_embeddings[nid] for nid in news_ids])

    # 6. Семантическое удаление рекламы
    ad_mask = filter_ad_by_embeddings(vectors, threshold=0.6)
    keep_indices = np.where(~ad_mask)[0]

    if len(keep_indices) < len(news_ids):
        logger.info(f"Удалено рекламы: {len(news_ids) - len(keep_indices)}")

    news_items = [news_items[i] for i in keep_indices]
    vectors = vectors[keep_indices]
    news_ids = [news_ids[i] for i in keep_indices]

    if not news_ids:
        return {"digest_id": str(digest_id), "status": "no_news_after_ad_filter"}

    # 7. Фильтрация по запросу (если указан)
    if request_data.get('filter_query'):
        filter_query = request_data['filter_query']
        query_emb = embedder.get_batch_embeddings([filter_query])[0]
        similarities = np.dot(vectors, query_emb)
        query_mask = similarities >= 0.28
        keep_indices = np.where(query_mask)[0]

        if len(keep_indices) < len(news_ids):
            logger.info(f"Не прошли фильтр по запросу: {len(news_ids) - len(keep_indices)}")

        news_items = [news_items[i] for i in keep_indices]
        vectors = vectors[keep_indices]
        news_ids = [news_ids[i] for i in keep_indices]

        if not news_ids:
            return {"digest_id": str(digest_id), "status": "no_news_after_semantic_filter"}

    # 8. Кластеризация
    n_clusters = min(request_data['n_clusters'], len(news_ids))
    if n_clusters == 0:
        return {"digest_id": str(digest_id), "status": "no_news_for_clustering"}
    clusters = await clustering_service.perform_clustering(digest_id, news_ids, n_clusters)
    if not clusters:
        return {"digest_id": str(digest_id), "status": "clustering_failed"}

    # 9. Суммаризация кластеров
    await summarization_service.summarize_clusters(digest_id)

    # 10. Сборка текста дайджеста
    digest_text = await build_digest_text(digest_id)
    await update_digest_text(digest_id, digest_text)

    # 11. Генерация аудио (если нужно)
    audio_path = None
    if request_data['output_format'] == 'audio' and digest_text:
        audio_path = await tts_service.generate_audio(digest_id, digest_text)

    # 12. Списание токенов
    await deduct_tokens(user_id, 1, f"Дайджест {digest_id}")

    # 13. Сохранение в историю
    await save_query_history(user_id, digest_id, request_data)

    return {
        "digest_id": str(digest_id),
        "status": "completed",
        "audio_path": audio_path
    }


# Вспомогательные функции (работают с БД)
async def build_digest_text(digest_id: uuid.UUID) -> str:
    async with async_session_maker() as session:
        stmt = select(Cluster).where(Cluster.digest_id == digest_id)
        clusters = (await session.execute(stmt)).scalars().all()
        parts = []
        for c in clusters:
            if c.title and c.summary_text:
                parts.append(f"📌 {c.title}\n{c.summary_text}\n")
        return "\n".join(parts)


async def update_digest_text(digest_id: uuid.UUID, digest_text: str):
    async with async_session_maker() as session:
        digest = await session.get(Digest, digest_id)
        if digest:
            digest.summary_text = digest_text
            await session.commit()


async def deduct_tokens(user_id: uuid.UUID, amount: int, description: str):
    async with async_session_maker() as session:
        user = await session.get(User, user_id)
        if user and user.token_balance >= amount:
            user.token_balance -= amount
            tx = TokenTransaction(
                user_id=user_id,
                amount=-amount,
                description=description
            )
            session.add(tx)
            await session.commit()


async def save_query_history(user_id: uuid.UUID, digest_id: uuid.UUID, request_data: Dict[str, Any]):
    async with async_session_maker() as session:
        qh = QueryHistory(
            user_id=user_id,
            digest_id=digest_id,
            query_params=json.dumps(request_data, default=str)
        )
        session.add(qh)
        await session.commit()