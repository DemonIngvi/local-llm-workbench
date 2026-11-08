# Local LLM Workbench

Локальный AI workbench для работы с языковыми моделями через единый интерфейс с интеграцией OpenCode и DeepSeek Harness.

## 🚀 Возможности

### Прямой чат
- **LibreChat UI** (порт 3200) - веб-интерфейс для чата с моделями
- **LiteLLM Proxy** (порт 4100) - управление доступом и квотами
- **LM Studio** (порт 1234) - локальный inference с поддержкой Qwen 2.5 и других моделей

### Безопасные агенты
- **OpenCode V2** - изолированный контейнер с безопасными разрешениями
- **DeepSeek Harness** - изолированный контейнер с профилем без `danger-full-access`
- **Task Registry API** (порт 8080) - HTTP API для управления задачами
- **Task Orchestrator** - автоматический запуск контейнеров по задачам

### Квоты и безопасность
- **PostgreSQL** - квоты для LiteLLM (TPM, RPM, бюджет)
- **Изоляция контейнеров** - непривилегированные пользователи, sandbox режим
- **Сетевая изоляция** - frontend/backend сети, нет доступа к интернету

## 📦 Быстрый старт

### 1. Установка зависимостей

**Windows:**
```powershell
# WSL 2
wsl --install

# Docker Desktop с WSL 2 backend
# LM Studio
```

**Linux:**
```bash
# Docker Engine + Compose plugin
sudo apt install docker.io docker-compose-plugin

# LM Studio или llmster daemon
curl -fsSL https://lmstudio.ai/install.sh | bash
```

### 2. Настройка LM Studio

⚠️ **Важно:** Настройте LM Studio для прослушивания на всех интерфейсах:

1. Откройте LM Studio → Developer → Local Server
2. Измените **Host** с `localhost` на `0.0.0.0`
3. Загрузите модель (например, `qwen2.5-coder-7b-instruct`)
4. Перезапустите сервер

Подробная инструкция: [docs/lm-studio-network-setup.md](docs/lm-studio-network-setup.md)

### 3. Инициализация проекта

```bash
# Создать конфигурацию
python scripts/setup.py init

# Запустить сервисы
python scripts/setup.py start

# Инициализировать БД LiteLLM (для квот)
pip install psycopg2-binary
python scripts/init_litellm_db.py
```

### 4. Открыть интерфейс

Откройте http://localhost:3200

Зарегистрируйтесь и выберите endpoint **Local LiteLLM**.

## 🎯 Использование оркестратора

### Создать задачу

```bash
curl -X POST http://localhost:8080/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Рефакторинг модуля авторизации",
    "workspace": "D:\\projects\\my-app",
    "harness": "opencode",
    "summary": "Упростить код, удалить дублирование"
  }'
```

Ответ:
```json
{"task_id": "1"}
```

### Выполнить задачу

```bash
# Автоматический запуск контейнера
python scripts/run_task.py 1

# С кастомным промптом
python scripts/run_task.py 1 --prompt "Используй TypeScript"
```

### Проверить статус

```bash
curl http://localhost:8080/tasks/1
```

Ответ:
```json
{
  "id": "1",
  "title": "Рефакторинг модуля авторизации",
  "harness": "opencode",
  "workspace": "D:\\projects\\my-app",
  "summary": "Задача выполнена успешно",
  "locked": false
}
```

Подробная документация: [docs/orchestrator-usage.md](docs/orchestrator-usage.md)

## 🏗️ Архитектура

```
┌─────────────────────────────────────────────────────────┐
│                    Windows Host                          │
│  ┌──────────────┐                                      │
│  │ LM Studio    │ :1234 (0.0.0.0)                      │
│  └──────┬───────┘                                      │
│         │                                               │
│  ┌──────┴───────┐                                      │
│  │ WSL 2        │                                      │
│  │ ┌──────────┐ │    ┌─────────────────────────────┐  │
│  │ │Docker    │ │    │ LibreChat UI :3200          │  │
│  │ │┌────────┐│ │    │ Task Registry API :8080     │  │
│  │ ││Frontend││◀┼────┤ LiteLLM Proxy :4100         │  │
│  │ ││Network ││ │    └─────────────────────────────┘  │
│  │ │└────────┘│ │                                      │
│  │ │    │     │ │    ┌─────────────────────────────┐  │
│  │ │┌────────┐│ │    │ PostgreSQL :5432            │  │
│  │ ││Backend ││◀┼────┤ MongoDB :27017              │  │
│  │ ││Network ││ │    │ Meilisearch :7700           │  │
│  │ │└────────┘│ │    └─────────────────────────────┘  │
│  │ └──────────┘ │                                      │
│  │              │    ┌─────────────────────────────┐  │
│  │              │    │ OpenCode Container          │  │
│  │              └───▶│ (on-demand, isolated)       │  │
│  │              │    │ DeepSeek Container          │  │
│  │              │    │ (on-demand, isolated)       │  │
│  │              │    └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

Подробная архитектура: [docs/architecture.md](docs/architecture.md)

## 🔒 Безопасность

### Изоляция контейнеров

**OpenCode:**
- Непривилегированный пользователь (UID 1001)
- White-list разрешений (только безопасные команды)
- Read-only файловая система
- Нет доступа к внешним сетям

**DeepSeek:**
- Непривилегированный пользователь (UID 1001)
- Sandbox режим workspace-write
- Блокировка опасных команд (rm, sudo, docker)
- Отключение телеметрии

### Сетевая изоляция
- **Frontend network**: LibreChat, пользовательские запросы
- **Backend network**: внутренние сервисы (LiteLLM, PostgreSQL, MongoDB)
- **Нет доступа к интернету** из контейнеров

### Квоты LiteLLM

| Ключ | TPM | RPM | Бюджет |
|------|-----|-----|--------|
| OpenCode | 1M | 100 | $10 |
| DeepSeek | 500K | 50 | $5 |

Подробная документация: [docs/security-configuration.md](docs/security-configuration.md)

## 🧪 Тестирование

```bash
# Запустить все тесты (30 тестов)
python -m unittest discover -s tests -v

# Smoke-тест LiteLLM
python scripts/docker_smoke.py
```

**Покрытие:**
- Task Registry API: 6 тестов
- OpenCode Client: 3 теста
- Orchestrator: 5 тестов
- E2E Orchestrator: 4 теста
- Init LiteLLM DB: 3 теста
- Setup: 3 теста
- Tasks: 3 теста
- Render BMAD: 3 теста

## 📚 Документация

- [Установка](docs/installation.md) - установка всех зависимостей
- [Подключение](docs/connection.md) - настройка сети и адресов
- [Архитектура](docs/architecture.md) - детальная архитектура системы
- [Использование оркестратора](docs/orchestrator-usage.md) - управление задачами
- [Безопасность](docs/security-configuration.md) - конфигурация безопасности
- [OpenCode интеграция](docs/opencode-integration.md) - интеграция OpenCode V2
- [LM Studio сеть](docs/lm-studio-network-setup.md) - настройка сети LM Studio
- [HTML документация](docs/bmad.html) - пользовательская версия BMAD

## 🛠️ Команды

```bash
# Инициализация конфигурации
python scripts/setup.py init

# Запуск всех сервисов
python scripts/setup.py start

# Остановка сервисов
python scripts/setup.py stop

# Статус контейнеров
python scripts/setup.py status

# Логи
python scripts/setup.py logs

# Инициализация БД LiteLLM
python scripts/init_litellm_db.py

# Выполнить задачу
python scripts/run_task.py <task_id>

# Запуск только OpenCode контейнера
docker compose --profile on-demand run opencode

# Запуск только DeepSeek контейнера
docker compose --profile on-demand run deepseek
```

## 📦 Структура проекта

```
local-llm-workbench/
├── scripts/                  # Python скрипты
│   ├── setup.py             # Инициализация и конфигурация
│   ├── tasks.py             # Реестр задач (SQLite)
│   ├── orchestrator.py      # Машина состояний OpenCode
│   ├── opencode_client.py   # HTTP клиент OpenCode V2
│   ├── task_registry_api.py # HTTP API для реестра задач
│   ├── run_task.py          # Оркестратор для запуска контейнеров
│   ├── init_litellm_db.py   # Инициализация БД LiteLLM
│   ├── docker_smoke.py      # Smoke-тест LiteLLM
│   └── render_bmad.py       # Генерация HTML документации
├── opencode/                 # OpenCode контейнер
│   ├── Dockerfile
│   ├── entrypoint.sh        # С интеграцией Task Registry API
│   └── opencode.json        # Безопасные разрешения
├── deepseek/                 # DeepSeek контейнер
│   ├── Dockerfile
│   ├── dsh-entrypoint.sh    # С интеграцией Task Registry API
│   └── cordis.patch.yml     # Изолированный профиль
├── tests/                    # Тесты (30 тестов)
│   ├── test_setup.py
│   ├── test_tasks.py
│   ├── test_opencode_client.py
│   ├── test_orchestrator.py
│   ├── test_render_bmad.py
│   ├── test_task_registry_api.py
│   ├── test_e2e_orchestrator.py
│   ├── test_init_litellm_db.py
│   └── docker-smoke/
├── docs/                     # Документация
│   ├── architecture.md
│   ├── installation.md
│   ├── connection.md
│   ├── security-configuration.md
│   ├── orchestrator-usage.md
│   ├── task-handoff.md
│   ├── opencode-integration.md
│   ├── lm-studio-network-setup.md
│   └── bmad.html
├── compose.yaml              # Docker Compose (с зафиксированными версиями)
├── start.sh                  # Linux/macOS запуск
├── start.ps1                 # Windows PowerShell запуск
├── start.cmd                 # Windows CMD запуск
└── README.md                 # Этот файл
```

## ⚙️ Конфигурация

### Переменные окружения (.env)

Создаётся автоматически при первом запуске:

```bash
# LiteLLM
LITELLM_MASTER_KEY=sk-...           # Master ключ LiteLLM
LITELLM_OPENCODE_KEY=sk-opencode-... # Ключ для OpenCode
LITELLM_DEEPSEEK_KEY=sk-deepseek-... # Ключ для DeepSeek
LITELLM_DB_PASSWORD=...              # Пароль PostgreSQL

# OpenCode
OPENCODE_SERVER_PASSWORD=...         # Пароль OpenCode сервера

# LM Studio
LM_STUDIO_API_KEY=not-needed         # API ключ LM Studio
LM_STUDIO_HOST_URL=http://localhost:1234/v1
LM_STUDIO_CONTAINER_URL=http://host.docker.internal:1234/v1

# LibreChat
CREDS_KEY=...                        # Ключ шифрования
JWT_SECRET=...                       # JWT секрет
MEILI_MASTER_KEY=...                 # Meilisearch ключ
```

### Зафиксированные версии образов

```yaml
postgres:17-alpine@sha256:3540c0362c80...
ghcr.io/berriai/litellm:main-stable@sha256:625981c83410...
mongo:8.0.20@sha256:098862b1339f...
getmeili/meilisearch:v1.35.1@sha256:8b57fc3c7f46...
registry.librechat.ai/librechat-ai/librechat-dev:latest@sha256:9625652b9d9a...
python:3.12-alpine@sha256:e064671ca452...
```

## 🐛 Известные ограничения

1. **LM Studio** должен слушать на `0.0.0.0` для доступа из WSL
2. **DeepSeek SDK** `sdk-minimal` имеет ограниченный доступ (не полная песочница)
3. **OpenCode V2** API экспериментальный, может измениться
4. **Task Registry** одноползовательский, нет аутентификации API
5. **SQLite** не подходит для высоких нагрузок (>100 задач/сек)

## ✅ Production readiness

- [x] Фиксация версий образов (digest)
- [x] Настройка квот LiteLLM через PostgreSQL
- [x] Полная интеграция контейнеров через Task Registry API
- [x] Оркестратор задач с E2E тестами
- [x] 30 unit-тестов проходят
- [x] Документация по безопасности
- [ ] Автоматический запуск harness из LibreChat UI
- [ ] Бэкапы данных
- [ ] HTTPS для внешних подключений

## 📄 Лицензия

MIT

## 🤝 Вклад

Проект находится в активной разработке. Основные направления:

- Интеграция с LibreChat UI для запуска задач
- Поддержка дополнительных harness
- Улучшение изоляции контейнеров
- Добавление мониторинга и метрик

## 📞 Поддержка

- GitHub Issues: https://github.com/DemonIngvi/local-llm-workbench/issues
- Документация OpenCode: https://opencode.ai/docs/
- Документация DeepSeek: https://github.com/deepseek-ai/deepseek-harness
- Документация LM Studio: https://lmstudio.ai/docs

## 📊 Статистика

- **Тесты**: 30 (все проходят)
- **Покрытие**: Task Registry API, OpenCode Client, Orchestrator, E2E, Setup, Tasks
- **Документация**: 8 markdown файлов + HTML версия
- **Коммиты**: 3 major commits
