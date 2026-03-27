from app.api.schemas.favorite_digest import SFavoriteDigestData


def build_favorite_digest_schema(fav, digest) -> SFavoriteDigestData:
    return SFavoriteDigestData(
        id=fav.id,
        digest_id=fav.digest_id,
        user_id=fav.user_id,
        title=digest.title,
        summary_text=digest.summary_text,
        filter_query=digest.filter_query,
        date_from=digest.date_from,
        date_to=digest.date_to,
        cluster_count=digest.cluster_count,
        audio_path=digest.audio_path,
        created_at=digest.created_at,
    )
