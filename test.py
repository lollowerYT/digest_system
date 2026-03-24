# # TODO: потом удалить этот файл, он нужен только для тестов, чтобы не удалять код из других файлов


# from jose import jwt
# from datetime import datetime, timedelta

# # Вставьте ваш ID из базы
# user_id = "630db693-f508-4af2-a5b7-c2b2103d6dbb"

# # Ваш SECRET_KEY из .env
# SECRET_KEY = "UaCFmvrKaQt46lWheulo11twbeJxNz3KkYsDRsr8GAI"
# ALGORITHM = "HS256"

# payload = {
#     "sub": user_id,
#     "exp": datetime.utcnow() + timedelta(days=7)
# }

# token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
# print(f"Your token:\n{token}")
import asyncio
import aiohttp

async def test():
    async with aiohttp.ClientSession() as session:
        async with session.get('https://api.telegram.org/bot8628318846:AAEWQzNzFO0-7aBgsBxiFseV7L8jIrNelLc/getMe') as resp:
            print(await resp.text())

asyncio.run(test())