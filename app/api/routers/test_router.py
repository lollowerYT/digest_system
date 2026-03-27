from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from app.config import settings

router = APIRouter(tags=["test"])

@router.get("/test_login", response_class=HTMLResponse)
async def index():
    html = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <title>Telegram Auth</title>
    </head>
    <body>
    <h2>Вход через Telegram</h2>
    <script async src="https://telegram.org/js/telegram-widget.js?22"
            data-telegram-login="{settings.WIDGET_BOT_USERNAME}"
            data-size="large"
            data-userpic="false"
            data-request-access="write"
            data-onauth="onTelegramAuth(user)">
    </script>
    <script>
        async function onTelegramAuth(user) {{
            console.log("Telegram user:", user);
            try {{
                const response = await fetch("/auth/telegram", {{
                    method: "POST",
                    headers: {{ "Content-Type": "application/json" }},
                    body: JSON.stringify(user)
                }});
                if (!response.ok) {{
                    throw new Error("Ошибка авторизации");
                }}
                const data = await response.json();
                console.log("JWT:", data.access_token);
                alert("Успешный вход!");
            }} catch (error) {{
                console.error(error);
                alert("Ошибка при авторизации");
            }}
        }}
    </script>
    </body>
    </html>
    """
    return html
