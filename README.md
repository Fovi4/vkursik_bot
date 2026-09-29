# Вкурсик — deploy package

Файлы:
- `main.py` — бот
- `database.py` — SQLite
- `requirements.txt` — Python-зависимости
- `.gitignore` — исключает токены, локальную БД и venv
- `render.yaml` — Blueprint для Render
- `.env.example` — пример переменных без секретов

## Локальный запуск

1. Создай `.env` на основе `.env.example`.
2. Установи зависимости:
   `pip install -r requirements.txt`
3. Запусти:
   `python main.py`

## Render

`render.yaml` настроен на Background Worker и persistent disk `/var/data`.

При создании Blueprint Render попросит:
- `BOT_TOKEN`
- `ADMIN_CHAT_ID`
- `WEBAPP_URL`

`DB_PATH` уже установлен в `/var/data/applications.db`.

Важно: настоящий `.env` и `applications.db` не коммить в GitHub.
