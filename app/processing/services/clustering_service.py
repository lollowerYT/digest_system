import uuid
import logging
from typing import List
import numpy as np
from sklearn.cluster import KMeans
import umap
from sqlalchemy import select

from app.database.models.cluster import Cluster
from app.database.models.cluster_news import ClusterNews
from app.database.models.embedding import Embedding
from app.database.models.embedding_projection import EmbeddingProjection
from app.database.database import async_session_maker

logger = logging.getLogger(__name__)

class ClusteringService:
    async def perform_clustering(self, digest_id: uuid.UUID, news_ids: List[uuid.UUID], n_clusters: int):
        async with async_session_maker() as session:
            # 1. Проверяем, есть ли уже кластеры для этого дайджеста
            stmt = select(Cluster).where(Cluster.digest_id == digest_id)
            existing_clusters = (await session.execute(stmt)).scalars().all()
            if existing_clusters:
                logger.info(f"Кластеры для дайджеста {digest_id} уже существуют, используем их")
                return existing_clusters

            # 2. Если нет – выполняем кластеризацию
            stmt = select(Embedding).where(Embedding.news_id.in_(news_ids))
            result = await session.execute(stmt)
            embeddings_rows = result.scalars().all()
            if len(embeddings_rows) == 0:
                return []

            emb_dict = {row.news_id: row.vector for row in embeddings_rows}
            valid_news_ids = [nid for nid in news_ids if nid in emb_dict]
            if len(valid_news_ids) < n_clusters:
                n_clusters = len(valid_news_ids)
            if n_clusters == 0:
                return []
            X = np.array([emb_dict[nid] for nid in valid_news_ids])

            # KMeans кластеризация
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            labels = kmeans.fit_predict(X)

            # UMAP проекция
            reducer = umap.UMAP(random_state=42)
            X_proj = reducer.fit_transform(X)

            clusters_map = {}
            for label in set(labels):
                cluster = Cluster(digest_id=digest_id)
                session.add(cluster)
                await session.flush()
                clusters_map[label] = cluster

            # Создаём связи и проекции
            for idx, (news_id, label) in enumerate(zip(valid_news_ids, labels)):
                cluster = clusters_map[label]
                cn = ClusterNews(cluster_id=cluster.id, news_id=news_id)
                session.add(cn)
                x, y = X_proj[idx]

                # Проверяем, есть ли уже проекция для этой новости в этом дайджесте
                stmt = select(EmbeddingProjection).where(
                    EmbeddingProjection.news_id == news_id,
                    EmbeddingProjection.digest_id == digest_id
                )
                existing_proj = (await session.execute(stmt)).scalar_one_or_none()
                if existing_proj:
                    # Если есть – пропускаем вставку
                    continue

                proj = EmbeddingProjection(
                    news_id=news_id,
                    cluster_id=cluster.id,
                    digest_id=digest_id,
                    x=float(x),
                    y=float(y)
                )
                session.add(proj)

            await session.commit()
            return list(clusters_map.values())