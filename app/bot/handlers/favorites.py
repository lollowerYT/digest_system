from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.digest import DigestDAO
from app.dao.favorite_digest import FavoriteDigestDAO
from app.database.models import User


router = Router()


@router.callback_query(F.data == "menu_favorites")
async def show_favorites(callback: CallbackQuery, session: AsyncSession, user: User):
    # TODO: Переделать под инлайн кнопки, добавить возможность удалить из БД
    results = []

    fav_digest_dao = FavoriteDigestDAO(session)
    digest_dao = DigestDAO(session)

    fav_digests_id = [digest.id for digest in await fav_digest_dao.get_user_favorite_digests(user.id)]

    if not fav_digests_id:
        await callback.answer("Дайджестов не найдено.")
    else:
        for digest_id in fav_digests_id:
            digest = await digest_dao.get_by_id(digest_id)

            results.append(
                f"<b>{digest.title}</b>\n\n"
                f"{digest.summary_text}\n"
                f"Дата создания: {digest.created_at.strftime('%d.%m.%Y')}\n\n"
                "-----------------------\n\n"
            )

    await callback.message.answer(''.join(results))
    await callback.answer()
