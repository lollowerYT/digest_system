@echo off
title Запуск системы анализа новостей
echo =====================================
echo Запуск системы анализа новостей
echo =====================================

:: Проверка, что мы в корневой папке проекта
if not exist app\main.py (
    echo Ошибка: Запустите скрипт из корневой папки проекта (где есть папка app).
    pause
    exit /b 1
)

:: Установка переменных окружения (при необходимости раскомментируйте)
:: set PATH=%PATH%;C:\Program Files\PostgreSQL\17\bin
:: set PATH=%PATH%;C:\Program Files\Redis

echo [1/5] Проверка PostgreSQL...
sc query postgresql-x64-17 | find "RUNNING" > nul
if errorlevel 1 (
    echo Служба PostgreSQL не запущена. Запускаем...
    net start postgresql-x64-17
    if errorlevel 1 (
        echo Не удалось запустить PostgreSQL. Проверьте установку и имя службы.
        pause
    )
) else (
    echo PostgreSQL уже запущен.
)

echo [2/5] Запуск Redis...
start "Redis Server" cmd /k "redis-server"
:: Небольшая пауза для инициализации Redis
timeout /t 2 /nobreak > nul

echo [3/5] Запуск ngrok (публичный адрес)...
where ngrok > nul 2>&1
if errorlevel 1 (
    echo ngrok не найден в PATH. Пропускаем запуск.
    echo При необходимости установите ngrok и добавьте в PATH.
) else (
    start "ngrok" cmd /k "ngrok http 8000"
)

echo [4/5] Запуск FastAPI...
start "FastAPI" cmd /k "uvicorn app.main:app --reload"

echo [5/5] Запуск Celery worker...
start "Celery Worker" cmd /k "celery -A app.processing.tasks.celery_app worker --loglevel=info --pool=solo"

echo =====================================
echo Все компоненты запущены.
echo Для остановки закройте все окна.
echo =====================================
pause