# Notes Telegram Bot (SQLite + MCP)

MVP: Telegram-бот для заметок, задач и напоминаний.
Данные в SQLite. Cursor читает БД через MCP на естественном языке.

## Стек

- Python 3.11+, aiogram v3, OpenAI SDK, FastAPI, FastMCP
- Два контейнера: `bot` (Telegram + scheduler), `api` (MCP HTTP)
- Общий volume с SQLite (`WAL`)

## Подготовка

1. Скопируйте `.env.example` в `.env` и заполните токены
   (`TELEGRAM_BOT_TOKEN`, `OPENAI_API_KEY` и опциональные
   параметры timezone / reminder time).
2. Выберите способ запуска: **venv** (локально) или **Docker**.

---

## Запуск через venv (локально)

### Создать и активировать окружение

**Windows (PowerShell):**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Linux / macOS:**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Старт сервисов (два терминала, venv активен)

```bash
# терминал 1 — API + MCP
uvicorn app.api.main:app --host 127.0.0.1 --port 8000

# терминал 2 — Telegram-бот + scheduler
python -m app.telegram.bot
```

### Остановка

- В каждом терминале: `Ctrl+C` — остановить uvicorn / бота.
- Деактивировать venv:

```bash
deactivate
```

Проверки:

- API: `http://127.0.0.1:8000/health` → `{"status":"ok"}`
- MCP: `http://127.0.0.1:8000/mcp` (см. `.cursor/mcp.json`)

---

## Запуск через Docker

### Старт

```bash
docker compose up --build -d
```

Фоновый режим (`-d`): контейнеры `bot` и `api`, общая БД
в volume `sqlite_data`.

Полезные команды:

```bash
docker compose ps          # статус
docker compose logs -f     # логи обоих сервисов
docker compose logs -f bot # только бот
```

После изменения кода бота (например, меню команд):

```bash
docker compose up -d --build bot
```

### Остановка

```bash
# остановить контейнеры (volume с БД сохраняется)
docker compose stop

# остановить и удалить контейнеры сети
docker compose down

# то же + удалить volume SQLite (данные будут потеряны)
docker compose down -v
```

---

## Команды бота и меню

Обработчики: `/start` `/note` `/task` `/reminder`
`/list_5` `/list_10`.

Меню команд в Telegram публикуется при старте бота через
`bot.set_my_commands()` в `app/telegram/bot.py`:

| Команда | Описание в меню |
|---|---|
| `/start` | Приветствие и инструкция |
| `/note` | Создать заметку |
| `/task` | Создать задачу |
| `/reminder` | Создать напоминание |
| `/list_5` | 5 последних записей |
| `/list_10` | 10 последних записей |

Если меню не видно сразу — переоткройте чат с ботом или
перезапустите клиент Telegram.

Пишите свободным текстом — intent определяет OpenAI.
Ответы — plain text (без MarkdownV2). Reply-клавиатуры нет;
у напоминаний — только inline-кнопки.

**Напоминания свободным текстом:** начинайте фразу со слова
«Напомни …», иначе сообщение часто распознаётся как обычная
задача без уведомления.

Пример: `Напомни мне завтра позвонить Андрею`

Альтернатива — команда `/reminder`, тогда тип фиксируется явно.

---

## MCP в Cursor

1. Запустите API (venv или Docker).
2. В Cursor Settings → MCP убедитесь, что сервер
   `notes-sqlite` из `.cursor/mcp.json` включён
   (`url`: `http://127.0.0.1:8000/mcp`).
3. В Agent/Composer задавайте вопросы обычным языком.

Примеры:

- Покажи все таблицы и их поля
- Выведи заметки за последние 3 дня
- Покажи напоминания на ближайшие 24 часа
- Найди заметки, где в заголовке есть «важно»

Tools (только чтение): `list_tables`, `describe_table`,
`list_notes`, `search_notes`, `list_tasks`, `list_reminders`.

---

## Тесты

Активируйте venv, затем:

```bash
python -m pytest -q
```

Smoke-проверка MCP внутри Docker (API должен быть Up):

```bash
docker compose cp scripts/docker_smoke.py api:/tmp/docker_smoke.py
docker compose exec -T -e PYTHONPATH=/app -w /app api python /tmp/docker_smoke.py
```

---

## Структура

```text
app/db/          схема и репозитории
app/services/    intent, clock, recurrence
app/telegram/    handlers, scheduler, меню команд
app/api/         FastAPI + MCP
scripts/         docker smoke-тесты
```
