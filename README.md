# Notes Telegram Bot (SQLite + MCP)

MVP: Telegram-бот для заметок, задач и напоминаний.
Данные в SQLite. Cursor читает БД через MCP на естественном языке.

## Стек

- Python 3.11+, aiogram v3, OpenAI SDK, FastAPI, FastMCP
- Два контейнера: `bot` (Telegram + scheduler), `api` (MCP HTTP)
- Общий volume с SQLite (`WAL`)

## Быстрый старт

1. Скопируйте `.env.example` в `.env` и заполните токены.
2. Установите зависимости:

```bash
pip install -r requirements.txt
```

3. Локально (два процесса):

```bash
# терминал 1 — API + MCP
uvicorn app.api.main:app --host 127.0.0.1 --port 8000

# терминал 2 — бот
python -m app.telegram.bot
```

4. Docker:

```bash
docker compose up --build
```

API: `http://127.0.0.1:8000/health`  
MCP: `http://127.0.0.1:8000/mcp` (см. `.cursor/mcp.json`)

## Команды бота

`/start` `/note` `/task` `/reminder` `/list_5` `/list_10`

Пишите свободным текстом — intent определяет OpenAI.
Ответы — plain text (без MarkdownV2).

## MCP в Cursor

После запуска API подключите сервер `notes-sqlite` из
`.cursor/mcp.json`. Примеры запросов:

- Покажи все таблицы и их поля
- Выведи заметки за последние 3 дня
- Покажи напоминания на ближайшие 24 часа
- Найди заметки, где в заголовке есть «важно»

Tools: `list_tables`, `describe_table`, `list_notes`,
`search_notes`, `list_tasks`, `list_reminders` (только чтение).

## Тесты

```bash
pytest -q
```

## Структура

```text
app/db/          схема и репозитории
app/services/    intent, clock, recurrence
app/telegram/    handlers, scheduler
app/api/         FastAPI + MCP
```
