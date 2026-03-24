# ! Данный роутер создан лишь для проверки некоторого функционала, в дальнейшем его необходимо удалить

from fastapi import APIRouter
from fastapi.responses import HTMLResponse


router = APIRouter(tags=["test"])

@router.get("/test_login", response_class=HTMLResponse)
async def index():
    # Простая HTML-страница с Telegram Login
    return """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <title>Telegram Auth</title>
    </head>
    <body>

    <h2>Вход через Telegram</h2>

    <!-- Telegram Login Widget -->
    <script async src="https://telegram.org/js/telegram-widget.js?22"
            data-telegram-login="Digest_Newsbot"
            data-size="large"
            data-userpic="false"
            data-request-access="write"
            data-onauth="onTelegramAuth(user)">
    </script>

    <script>
        async function onTelegramAuth(user) {
            console.log("Telegram user:", user);

            try {
                const response = await fetch("/auth/telegram", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify(user)
                });

                if (!response.ok) {
                    throw new Error("Ошибка авторизации");
                }

                const data = await response.json();

                console.log("JWT:", data.access_token);

                alert("Успешный вход!");

            } catch (error) {
                console.error(error);
                alert("Ошибка при авторизации");
            }
        }
    </script>

    </body>
    </html>
    """


@router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard():
    with open("app/templates/admin_dashboard.html", "r", encoding="utf-8") as f:
        return f.read()
