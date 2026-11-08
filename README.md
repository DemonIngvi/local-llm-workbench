# Local LLM Workbench

Локальный AI workbench для работы с языковыми моделями через единый интерфейс с интеграцией OpenCode и DeepSeek Harness.

## 🚀 Быстрый старт

### 1. Установка зависимостей

**Windows:**
- WSL 2: `wsl --install`
- Docker Desktop с WSL 2 backend
- LM Studio (не устанавливается этим проектом)

**Linux:**
- Docker Engine + Compose plugin
- LM Studio или llmster daemon

### 2. Настройка LM Studio

⚠️ **Важно:** Настройте LM Studio для прослушивания на всех интерфейсах:

1. Откройте LM Studio → Developer → Local Server
2. Измените **Host** с `localhost` на `0.0.0.0`
3. Перезапустите сервер

Подробная инструкция: [docs/lm-studio-network-setup.md](docs/lm-studio-network-setup.md)

### 3. Запуск стенда

```bash
# Инициализация конфигурации
python scripts/setup.py init

# Запуск всех сервисов
python scripts/setup.py start
```

### 4. Открыть интерфейс

http://localhost:3200

Зарегистрируйтесь и выберите endpoint **Local LiteLLM**.

## 📋 Возможности

### ✅ Реализовано

- **Прямой чат** с моделями через LibreChat → LiteLLM → LM Studio
- **Реестр задач** с SQLite для маршрутизации между harness
- **HTTP API** для управления задачами (порт 8080)
- **Изолированный OpenCode V2** контейнер с безопасными разрешениями
- **Изолированный DeepSeek** контейнер с профилем без `danger-full-access`
- **PostgreSQL** для квот LiteLLM
- **HTTP API реестра задач** для интеграции контейнеров
- **17 unit-тестов** (все проходят)
- **Docker smoke-тест** LiteLLM

### ⚠️ В разработке

- Полная интеграция контейнеров через Task Registry API
- Автоматический запуск harness из LibreChat
- E2E тестирование с реальным LM Studio
- Фиксация версий образов (digest)

## 🏗️ Архитектура

```
┌─────────────────────────────────────────────────┐
│              LibreChat UI :3200                  │
│         (веб-интерфейс для чата)                │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│              LiteLLM Proxy :4100                 │
│    (управление доступом, квоты, маршрутизация)  │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│              LM Studio :1234                     │
│         (локальные модели, inference)            │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│           Task Registry API :8080                 │
│    (управление задачами, handoff, блокировки)     │
└────────────────┬──────────────────────────────────┘
                 │
    ┌────────────┴────────────┐
    │                         │
┌───▼──────┐            ┌─────▼─────┐
│ OpenCode │            │ DeepSeek  │
│Container │            │ Container │
│(по запросу)│          │(по запросу)│
└───────────┘            └───────────┘
```

Подробная архитектура: [docs/architecture.md](docs/architecture.md)

## 🔒 Безопасность

### Изоляция контейнеров

**OpenCode:**
- Непривилегированный пользователь
- White-list разрешений (только безопасные команды)
- Нет доступа к внешним сетям
- Read-only файловая система (кроме workspace)

**DeepSeek:**
- Непривилегированный пользователь
- Sandbox режим `workspace-write`
- Блокировка опасных команд (rm, sudo, docker)
- Отключение телеметрии

### Сетевая изоляция

- Frontend network: LibreChat, пользовательские запросы
- Backend network: Внутренние сервисы (LiteLLM, PostgreSQL)
- Нет доступа к интернету из контейнеров

Подробная документация: [docs/security-configuration.md](docs/security-configuration.md)

## 📚 Документация

- [Установка](docs/installation.md) - установка всех зависимостей
- [Подключение](docs/connection.md) - настройка сети и адресов
- [Архитектура](docs/architecture.md) - детальная архитектура системы
- [Безопасность](docs/security-configuration.md) - конфигурация безопасности
- [Реестр задач](docs/task-handoff.md) - управление задачами и handoff
- [OpenCode интеграция](docs/opencode-integration.md) - интеграция OpenCode V2
- [LM Studio сеть](docs/lm-studio-network-setup.md) - настройка сети LM Studio
- [HTML документация](docs/bmad.html) - пользовательская версия BMAD

## 🧪 Тестирование

```bash
# Unit-тесты (17 тестов)
python -m unittest discover -s tests -v

# Docker smoke-тест LiteLLM (требует Docker)
python scripts/docker_smoke.py

# Проверка Task Registry API
curl http://localhost:8080/health
```

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
│   ├── docker_smoke.py      # Smoke-тест LiteLLM
│   └── render_bmad.py       # Генерация HTML документации
├── opencode/                 # OpenCode контейнер
│   ├── Dockerfile
│   ├── entrypoint.sh
│   └── opencode.json        # Безопасные разрешения
├── deepseek/                 # DeepSeek контейнер
│   ├── Dockerfile
│   ├── dsh-entrypoint.sh
│   └── cordis.patch.yml     # Изолированный профиль
├── tests/                    # Тесты
│   ├── test_setup.py
│   ├── test_tasks.py
│   ├── test_opencode_client.py
│   ├── test_orchestrator.py
│   ├── test_render_bmad.py
│   ├── test_task_registry_api.py
│   └── docker-smoke/
├── docs/                     # Документация
│   ├── architecture.md
│   ├── installation.md
│   ├── connection.md
│   ├── security-configuration.md
│   ├── task-handoff.md
│   ├── opencode-integration.md
│   ├── lm-studio-network-setup.md
│   └── bmad.html
├── compose.yaml              # Docker Compose конфигурация
├── start.sh                  # Linux/macOS запуск
├── start.ps1                 # Windows PowerShell запуск
├── start.cmd                 # Windows CMD запуск
└── README.md                 # Этот файл
```

## ⚙️ Конфигурация

### Переменные окружения (.env)

Создаётся автоматически при первом запуске:

```bash
LITELLM_MASTER_KEY=sk-...           # Master ключ LiteLLM
LITELLM_OPENCODE_KEY=sk-...         # Ключ для OpenCode
LITELLM_DEEPSEEK_KEY=sk-...         # Ключ для DeepSeek
LM_STUDIO_API_KEY=not-needed        # API ключ LM Studio
LM_STUDIO_HOST_URL=http://localhost:1234/v1
LM_STUDIO_CONTAINER_URL=http://host.docker.internal:1234/v1
CREDS_KEY=...                        # Ключ шифрования LibreChat
CREDS_IV=...                         # IV шифрования LibreChat
JWT_SECRET=...                       # JWT секрет
JWT_REFRESH_SECRET=...               # JWT refresh секрет
MEILI_MASTER_KEY=...                 # Meilisearch ключ
OPENCODE_SERVER_PASSWORD=...         # Пароль OpenCode сервера
LITELLM_DB_PASSWORD=...              # Пароль PostgreSQL
```

### Модели

Автоматически обнаруживаются из LM Studio при запуске. Поддерживаются все модели, доступные в LM Studio.

## 🐛 Известные ограничения

1. **LM Studio** слушает только на localhost - требуется настройка
2. **DeepSeek SDK** `sdk-minimal` имеет ограниченный доступ (не полная песочница)
3. **OpenCode V2** API экспериментальный, может измениться
4. **Task Registry** одноползовательский, нет аутентификации API
5. **SQLite** не подходит для высоких нагрузок (>100 задач/сек)
6. **Версии образов** не зафиксированы (используются `latest` теги)

## 🚧 Production readiness

Для production использования необходимо:

1. ✅ Фиксация версий всех образов (digest вместо tags)
2. ⚠️ Настройка PostgreSQL с квотами (контейнер добавлен, квоты не настроены)
3. ⚠️ Полная интеграция контейнеров через Task Registry API
4. ❌ Автоматический запуск harness из LibreChat UI
5. ❌ E2E тестирование с реальным LM Studio
6. ✅ Мониторинг и алертинг (логи Docker)
7. ❌ Бэкапы данных
8. ❌ HTTPS для внешних подключений

## 📄 Лицензия

MIT

## 🤝 Вклад

Проект находится в активной разработке. Основные направления:

- Интеграция контейнеров через Task Registry API
- Автоматический запуск harness из LibreChat
- E2E тестирование
- Улучшение изоляции DeepSeek
- Добавление поддержки других harness

## 📞 Поддержка

- GitHub Issues: https://github.com/DemonIngvi/local-llm-workbench/issues
- Документация OpenCode: https://opencode.ai/docs/
- Документация DeepSeek: https://github.com/deepseek-ai/deepseek-harness
- Документация LM Studio: https://lmstudio.ai/docs
