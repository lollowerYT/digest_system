# services/embedding_service.py
import uuid
import numpy as np
from typing import List
from sqlalchemy import select
from app.database.models.news import News
from app.database.models.embedding import Embedding
from app.database.database import async_session_maker
from app.processing.models.qwen_embedder import QwenEmbedder

class EmbeddingService:
    def __init__(self, embedder: QwenEmbedder):
        self.embedder = embedder

    async def generate_for_news_ids(self, news_ids: List[uuid.UUID]) -> List[Embedding]:
        async with async_session_maker() as session:
            stmt = select(News).where(News.id.in_(news_ids))
            result = await session.execute(stmt)
            news_list = result.scalars().all()
            if not news_list:
                return []

            texts = [n.text for n in news_list]
            embeddings = self.embedder.get_batch_embeddings(texts)

            saved = []
            for news, vec in zip(news_list, embeddings):
                stmt_emb = select(Embedding).where(Embedding.news_id == news.id)
                existing = await session.execute(stmt_emb)
                if existing.scalar_one_or_none():
                    continue
                vector_list = vec.tolist() if isinstance(vec, np.ndarray) else vec
                emb = Embedding(news_id=news.id, vector=vector_list)
                session.add(emb)
                saved.append(emb)
            await session.commit()
            for emb in saved:
                await session.refresh(emb)
            return saved

    async def save_embeddings(self, news_ids: List[uuid.UUID], embeddings: List[np.ndarray]):
        if not news_ids:
            return
        async with async_session_maker() as session:
            stmt = select(Embedding.news_id).where(Embedding.news_id.in_(news_ids))
            existing = await session.execute(stmt)
            existing_ids = {row[0] for row in existing}

            to_insert = []
            for nid, vec in zip(news_ids, embeddings):
                if nid not in existing_ids:
                    emb_obj = Embedding(
                        news_id=nid,
                        vector=vec.tolist() if isinstance(vec, np.ndarray) else vec
                    )
                    to_insert.append(emb_obj)

            if to_insert:
                session.add_all(to_insert)
                await session.commit()