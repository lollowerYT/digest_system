from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.middleware.logging import log_requests_middleware
from app.api.routers.auth_router import router as auth_router
from app.api.routers.user_router import router as user_router
from app.api.routers.admin_router import router as admin_router
from app.api.routers.test_router import router as test_router
from app.api.routers.subscription_router import router as subscription_router
from app.api.routers.digest_router import router as digest_router
from app.api.routers.favorite_digest_router import router as favorite_digest_router
from app.api.routers.cluster_router import router as cluster_router
from app.api.routers.channel_router import router as channel_router


app = FastAPI() # Создаем экземпляр приложения

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://overmasterful-aerologic-katelynn.ngrok-free.dev",
        "http://localhost:5173"
    ],
    expose_headers=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Добавляем middlewares
app.middleware("https")(log_requests_middleware)


app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Подключаем все роутеры
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(admin_router)
app.include_router(subscription_router)
app.include_router(digest_router)
app.include_router(favorite_digest_router)
app.include_router(cluster_router)
app.include_router(channel_router)


# Тестовый роутер
app.include_router(test_router)
