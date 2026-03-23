"""add_digest_id_to_embedding_projections

Revision ID: c284416d2979
Revises: e09ccd5cabeb
Create Date: 2026-03-24 00:05:12.654158

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'c284416d2979'
down_revision: Union[str, Sequence[str], None] = 'e09ccd5cabeb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Добавляем колонку digest_id (можно nullable, но затем заполним)
    op.add_column('embedding_projections',
                  sa.Column('digest_id', UUID(as_uuid=True), nullable=True))
    # Заполняем digest_id из связанного кластера
    op.execute("""
        UPDATE embedding_projections ep
        SET digest_id = c.digest_id
        FROM clusters c
        WHERE ep.cluster_id = c.id
    """)
    # Делаем колонку NOT NULL
    op.alter_column('embedding_projections', 'digest_id', nullable=False)
    # Добавляем внешний ключ
    op.create_foreign_key('embedding_projections_digest_id_fkey', 'embedding_projections',
                          'digests', ['digest_id'], ['id'])
    # Удаляем старое уникальное ограничение на news_id
    op.drop_constraint('embedding_projections_news_id_key', 'embedding_projections', type_='unique')
    # Создаём новое уникальное ограничение на (news_id, digest_id)
    op.create_unique_constraint('embedding_projections_news_digest_unique',
                                'embedding_projections', ['news_id', 'digest_id'])

def downgrade():
    op.drop_constraint('embedding_projections_news_digest_unique', 'embedding_projections', type_='unique')
    op.create_unique_constraint('embedding_projections_news_id_key', 'embedding_projections', ['news_id'])
    op.drop_constraint('embedding_projections_digest_id_fkey', 'embedding_projections', type_='foreignkey')
    op.drop_column('embedding_projections', 'digest_id')