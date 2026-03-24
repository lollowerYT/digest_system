import plotly.express as px
from sqlalchemy import select
from app.database.models.embedding_projection import EmbeddingProjection
from app.database.models.cluster import Cluster
from app.database.database import async_session_maker

async def plot_clusters(digest_id):
    async with async_session_maker() as session:
        stmt = (
            select(EmbeddingProjection, Cluster.title)
            .join(Cluster, EmbeddingProjection.cluster_id == Cluster.id)
            .where(Cluster.digest_id == digest_id)
        )
        result = await session.execute(stmt)
        rows = result.all()

        data = {
        "x": [row[0].x for row in rows],
        "y": [row[0].y for row in rows],
        "cluster_title": [row[1] for row in rows],
        }

        fig = px.scatter(
                data,
                x="x",
                y="y",
                color="cluster_title",
                title="Визуализация распределения новостей по тематическим группам"
            )
        fig.update_xaxes(
            showgrid=False,
            showticklabels=False,
            title="X",
            showline=True,      
            linewidth=1,
            linecolor="black"
        )
        
        fig.update_yaxes(
            showgrid=False,
            showticklabels=False,
            title="Y",
            showline=True,
            linewidth=1,
            linecolor="black"
        )
        
        fig.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white",
            legend_title_text="Тематика",
            showlegend=True
        )
        
        #fig.show(renderer="browser")
        fig.show()
