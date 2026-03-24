import asyncio
import uuid
import json
import logging
import numpy as np
from datetime import datetime
from typing import Dict, Any, List
from celery import chain
from app.processing.tasks.celery_app import celery_app
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

logger = logging.getLogger(__name__)

# Глобальные переменные для ленивой загрузки
_collector = None
_embedder = None
_summarizer = None
_tts_engine = None
_embedding_service = None
_clustering_service = None
_summarization_service = None
_tts_service = None

def _init_services():
    """Ленивая инициализация сервисов (загружаются только при первом вызове)"""
    global _collector, _embedder, _summarizer, _tts_engine
    global _embedding_service, _clustering_service, _summarization_service, _tts_service
    
    if _collector is not None:
        return
    
    logger.info("🚀 Инициализация сервисов...")
    
    from app.processing.services.telegram_collector import TelegramCollector
    from app.processing.models.qwen_embedder import QwenEmbedder
    from app.processing.models.summarizer import SaigaSummarizer
    from app.processing.models.tts import SileroTTS
    from app.processing.services.embedding_service import EmbeddingService
    from app.processing.services.clustering_service import ClusteringService
    from app.processing.services.summarization_service import SummarizationService
    from app.processing.services.tts_service import TTSService
    from app.processing.utils.filtering import set_embedder, get_ad_embedding
    
    _collector = TelegramCollector(
        api_id=settings.API_ID,
        api_hash=settings.API_HASH,
        phone=settings.PHONE_NUMBER
    )
    
    _embedder = QwenEmbedder(
        model_name="Qwen/Qwen3-Embedding-0.6B",
        device="cuda",          # используем CPU для экономии памяти
        embedding_dim=1024
    )
    
    set_embedder(_embedder)
    get_ad_embedding()
    
    _summarizer = SaigaSummarizer(
        model_name=settings.SAIGA_MODEL,
        host=settings.OLLAMA_HOST
    )
    
    _tts_engine = SileroTTS(speaker='xenia')
    
    _embedding_service = EmbeddingService(_embedder)
    _clustering_service = ClusteringService()
    _summarization_service = SummarizationService(_summarizer)
    _tts_service = TTSService(_tts_engine)
    
    logger.info("✅ Сервисы инициализированы")


@celery_app.task(bind=True)
def generate_digest(self, user_id: str, digest_id: str, request_data: Dict[str, Any]):
    """Задача на создание дайджеста"""
    _init_services()  # инициализируем сервисы при первом вызове
    
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
    global _collector, _embedder, _embedding_service, _clustering_service
    global _summarization_service, _tts_service
    
    logger.info(f"🚀 Начало обработки дайджеста {digest_id} для пользователя {user_id}")
    logger.info(f"📋 Параметры: каналы={request_data['channels']}, "
                f"даты={request_data['date_from']}..{request_data['date_to']}, "
                f"кластеров={request_data['n_clusters']}, "
                f"формат={request_data['output_format']}")
    
    # 1. Получаем каналы из БД
    async with async_session_maker() as session:
        stmt = select(TelegramChannel).where(
            TelegramChannel.username.in_(request_data['channels'])
        )
        result = await session.execute(stmt)
        channels = result.scalars().all()
        logger.info(f"📡 Найдено активных каналов: {len(channels)}")
        if not channels:
            logger.warning(f"⚠️ Нет активных каналов для дайджеста {digest_id}")
            return {"digest_id": str(digest_id), "status": "no_active_channels"}

    # 2. Сбор новостей (парсинг + загрузка всех из БД)
    date_from = datetime.fromisoformat(request_data['date_from'])
    date_to = datetime.fromisoformat(request_data['date_to'])
    logger.info(f"🕒 Начинаем сбор новостей с {date_from} по {date_to}")

    # Сначала парсим и сохраняем новые сообщения (если есть)
    await _collector.collect_news_for_channels(channels, date_from)

    # Теперь загружаем все сообщения за период из БД
    async with async_session_maker() as session:
        stmt = (
            select(News)
            .where(News.channel_id.in_([c.id for c in channels]))
            .where(News.published_at >= date_from)
            .where(News.published_at <= date_to)
        )
        result = await session.execute(stmt)
        news_items = result.scalars().all()
        logger.info(f"📰 Всего новостей за период: {len(news_items)}")

    if not news_items:
        logger.warning(f"⚠️ Новостей не найдено для дайджеста {digest_id}")
        return {"digest_id": str(digest_id), "status": "no_news"}

    # Дальше идёт существующий код (извлечение id, текстов, эмбеддинги, кластеризация...)
    news_ids = [n.id for n in news_items]
    texts = [n.text for n in news_items]

    # 3. Загружаем существующие эмбеддинги
    async with async_session_maker() as session:
        stmt = select(Embedding.news_id, Embedding.vector).where(Embedding.news_id.in_(news_ids))
        rows = await session.execute(stmt)
        existing_embeddings = {row.news_id: np.array(row.vector) for row in rows}
        logger.info(f"🧠 Уже есть эмбеддинги для {len(existing_embeddings)} новостей")

    # 4. Генерируем эмбеддинги для новых новостей (тех, у которых ещё нет)
    missing_indices = [i for i, nid in enumerate(news_ids) if nid not in existing_embeddings]
    if missing_indices:
        missing_texts = [texts[i] for i in missing_indices]
        missing_ids = [news_ids[i] for i in missing_indices]
        logger.info(f"🔄 Генерация эмбеддингов для {len(missing_ids)} новых новостей")
        new_vectors = _embedder.get_batch_embeddings(missing_texts)
        await _embedding_service.save_embeddings(missing_ids, new_vectors)
        for nid, vec in zip(missing_ids, new_vectors):
            existing_embeddings[nid] = vec

    # 5. Собираем матрицу эмбеддингов
    vectors = np.array([existing_embeddings[nid] for nid in news_ids])
    logger.info(f"📊 Матрица эмбеддингов: {vectors.shape}")

    # 6. Семантическое удаление рекламы
    from app.processing.utils.filtering import filter_ad_by_embeddings
    ad_mask = filter_ad_by_embeddings(vectors, threshold=0.6)
    keep_indices = np.where(~ad_mask)[0]
    removed_count = len(news_ids) - len(keep_indices)
    if removed_count > 0:
        logger.info(f"🚫 Удалено рекламы: {removed_count} новостей")

    news_items = [news_items[i] for i in keep_indices]
    vectors = vectors[keep_indices]
    news_ids = [news_ids[i] for i in keep_indices]

    if not news_ids:
        logger.warning(f"⚠️ После фильтрации рекламы новостей не осталось")
        return {"digest_id": str(digest_id), "status": "no_news_after_ad_filter"}

    # 7. Фильтрация по запросу
    if request_data.get('filter_query'):
        filter_query = request_data['filter_query']
        logger.info(f"🎯 Применяем семантический фильтр: '{filter_query}'")
        query_emb = _embedder.get_batch_embeddings([filter_query])[0]
        similarities = np.dot(vectors, query_emb)
        query_mask = similarities >= 0.28
        keep_indices = np.where(query_mask)[0]
        removed_by_query = len(news_ids) - len(keep_indices)
        if removed_by_query > 0:
            logger.info(f"🔍 Отсеяно по запросу: {removed_by_query} новостей")

        news_items = [news_items[i] for i in keep_indices]
        vectors = vectors[keep_indices]
        news_ids = [news_ids[i] for i in keep_indices]

        if not news_ids:
            logger.warning(f"⚠️ После фильтрации по запросу новостей не осталось")
            return {"digest_id": str(digest_id), "status": "no_news_after_semantic_filter"}

    # 8. Кластеризация
    n_clusters = min(request_data['n_clusters'], len(news_ids))
    logger.info(f"🔢 Кластеризация {len(news_ids)} новостей на {n_clusters} кластеров")
    clusters = await _clustering_service.perform_clustering(digest_id, news_ids, n_clusters)
    if not clusters:
        logger.error(f"❌ Ошибка кластеризации для дайджеста {digest_id}")
        return {"digest_id": str(digest_id), "status": "clustering_failed"}
    logger.info(f"✅ Создано кластеров: {len(clusters)}")

    # 9. Суммаризация кластеров
    logger.info(f"📝 Запуск суммаризации кластеров...")
    await _summarization_service.summarize_clusters(digest_id)
    logger.info(f"✅ Суммаризация завершена")

    # 10. Сборка текста дайджеста
    digest_text = await build_digest_text(digest_id)
    await update_digest_text(digest_id, digest_text)
    logger.info(f"📄 Текст дайджеста сформирован (длина {len(digest_text)} символов)")

    # 11. Генерация аудио
    audio_path = None
    if request_data['output_format'] == 'audio' and digest_text:
        logger.info(f"🔊 Генерация аудио для дайджеста {digest_id}, текст: {len(digest_text)} символов")
        try:
            audio_path = await _tts_service.generate_audio(digest_id, digest_text)
            if audio_path:
                logger.info(f"🎵 Аудио сохранено: {audio_path}")
            else:
                logger.warning(f"⚠️ Не удалось сгенерировать аудио: вернулся None")
        except Exception as e:
            logger.error(f"❌ Исключение при генерации аудио: {e}", exc_info=True)
            audio_path = None

    # 12. Списание токенов (разная стоимость для текста и аудио)
    token_cost = 5 if request_data['output_format'] == 'audio' else 1
    await deduct_tokens(user_id, token_cost, f"Дайджест {digest_id} (формат {request_data['output_format']})")
    logger.info(f"💰 Списано {token_cost} токенов у пользователя {user_id} за дайджест в формате {request_data['output_format']}")

    # 13. Сохранение в историю
    await save_query_history(user_id, digest_id, request_data)
    logger.info(f"📜 История запроса сохранена")

    logger.info(f"🎉 Дайджест {digest_id} успешно обработан")
    return {
        "digest_id": str(digest_id),
        "status": "completed",
        "audio_path": audio_path
    }


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