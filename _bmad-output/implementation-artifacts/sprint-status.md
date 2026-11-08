# Статус спринта

## Завершённые задачи

### E1: Локальный чат (100%)
- [x] S1.1: Настройка LM Studio для прослушивания на всех интерфейсах
- [x] S1.2: Конфигурация LibreChat для подключения к LiteLLM
- [x] S1.3: Интеграция OpenCode V2 через LiteLLM
- [x] S1.4: E2E тестирование прямого чата

### E2: Безопасные агенты (100%)
- [x] S2.1: Создан изолированный контейнер OpenCode V2 с безопасными разрешениями
- [x] S2.2: Создан изолированный контейнер DeepSeek с профилем без danger-full-access
- [x] S2.3: Task Registry API для управления задачами
- [x] S2.4: HTTP API для интеграции контейнеров
- [x] S2.5: PostgreSQL для квот LiteLLM
- [x] S2.6: Оркестратор задач для запуска контейнеров
- [x] S2.7: E2E тесты с моками для полного пути выполнения задач

### E3: Воспроизводимость и качество (100%)
- [x] S3.1: Зафиксированы версии всех Docker образов (digest)
- [x] S3.2: Настроены квоты LiteLLM через PostgreSQL
- [x] S3.3: Создана документация по использованию оркестратора
- [x] S3.4: 30 unit-тестов проходят (Windows и WSL)

## Статистика

- **Всего тестов**: 30
- **Проходят**: 30 (100%)
- **Покрытие**:
  - Task Registry API: 6 тестов
  - OpenCode Client: 3 теста
  - Orchestrator: 5 тестов
  - E2E Orchestrator: 4 теста
  - Init LiteLLM DB: 3 теста
  - Setup: 3 теста
  - Tasks: 3 теста
  - Render BMAD: 3 теста

## Зафиксированные версии образов

```yaml
postgres:17-alpine@sha256:3540c0362c809df084ffac0ae69fe794515f9de92692f02178bcdce0ef0302ac
ghcr.io/berriai/litellm:main-stable@sha256:625981c83410a3ea68eb0697590a57ec1d764d634514d54fa5db0591077ee839
mongo:8.0.20@sha256:098862b1339f031900ca66cf8fef799e616d6324fa41b9a263f2ec899552c1ef
getmeili/meilisearch:v1.35.1@sha256:8b57fc3c7f46535ddef3828df1538465ac19d892eb57c9a10da6df0880bd5856
registry.librechat.ai/librechat-ai/librechat-dev:latest@sha256:9625652b9d9ac9fbf9ff3505fc34770f822c7aa079f58d06b4e66eed2dc93aeb
python:3.12-alpine@sha256:e064671ca452259bab50e8e2c7bd896e39e9a343bb06ca25234adf6fe18d0fc7
```

## Архитектура

```
┌─────────────────────────────────────────────────────────┐
│                    Windows Host                          │
│  ┌──────────────┐                                      │
│  │ LM Studio    │ :1234 (0.0.0.0)                      │
│  └──────┬───────┘                                      │
│         │                                               │
│  ┌──────┴───────┐                                      │
│  │ WSL 2        │                                      │
│  │ ┌──────────┐ │                                      │
│  │ │Docker    │ │                                      │
│  │ │┌────────┐│ │    ┌─────────────────────────────┐  │
│  │ ││Frontend││◀┼────┤ LibreChat :3200             │  │
│  │ ││Network ││ │    └─────────────────────────────┘  │
│  │ │└────────┘│ │                                      │
│  │ │    │     │ │    ┌─────────────────────────────┐  │
│  │ │┌────────┐│ │    │ Task Registry API :8080     │  │
│  │ ││Backend ││◀┼────┤ (HTTP REST API)             │  │
│  │ ││Network ││ │    └─────────────────────────────┘  │
│  │ │└────────┘│ │                                      │
│  │ │    │     │ │    ┌─────────────────────────────┐  │
│  │ │    │     │ │    │ LiteLLM :4100               │  │
│  │ │    ├─────┼─┼───▶│ (OpenAI-compatible proxy)   │  │
│  │ │    │     │ │    └─────────────────────────────┘  │
│  │ │    │     │ │                                      │
│  │ │    │     │ │    ┌─────────────────────────────┐  │
│  │ │    │     │ │    │ PostgreSQL :5432            │  │
│  │ │    │     │ └───▶│ (LiteLLM quotas)            │  │
│  │ │    │     │      └─────────────────────────────┘  │
│  │ │    │     │                                      │
│  │ │    │     │    ┌─────────────────────────────┐  │
│  │ │    │     │    │ MongoDB :27017              │  │
│  │ │    │     └───▶│ (LibreChat storage)         │  │
│  │ │    │          └─────────────────────────────┘  │
│  │ │    │                                          │
│  │ │    │    ┌─────────────────────────────┐      │
│  │ │    └────┤ Meilisearch :7700           │      │
│  │ │         │ (LibreChat search)          │      │
│  │ │         └─────────────────────────────┘      │
│  │ │                                              │
│  │ │    ┌─────────────────────────────┐          │
│  │ └────┤ OpenCode Container          │          │
│  │      │ (on-demand, isolated)       │          │
│  │      └─────────────────────────────┘          │
│  │                                              │
│  │      ┌─────────────────────────────┐          │
│  └──────┤ DeepSeek Container          │          │
│         │ (on-demand, isolated)       │          │
│         └─────────────────────────────┘          │
└──────────────────────────────────────────────────┘
```

## Квоты LiteLLM

### OpenCode Key
- TPM (токенов/мин): 1,000,000
- RPM (запросов/мин): 100
- Budget: $10.00

### DeepSeek Key
- TPM (токенов/мин): 500,000
- RPM (запросов/мин): 50
- Budget: $5.00

## Безопасность

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
- Frontend network: LibreChat, пользовательские запросы
- Backend network: внутренние сервисы
- Нет доступа к интернету из контейнеров

## Использование

### 1. Инициализация

```bash
# Создать конфигурацию
python scripts/setup.py init

# Запустить сервисы
python scripts/setup.py start

# Инициализировать БД LiteLLM
pip install psycopg2-binary
python scripts/init_litellm_db.py
```

### 2. Создать задачу

```bash
curl -X POST http://localhost:8080/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Рефакторинг модуля",
    "workspace": "D:\\projects\\my-app",
    "harness": "opencode",
    "summary": "Упростить код"
  }'
```

### 3. Выполнить задачу

```bash
python scripts/run_task.py <task_id>
```

## Документация

- [Архитектура](docs/architecture.md)
- [Использование оркестратора](docs/orchestrator-usage.md)
- [Безопасность](docs/security-configuration.md)
- [Интеграция OpenCode](docs/opencode-integration.md)
- [Настройка LM Studio](docs/lm-studio-network-setup.md)

## GitHub

Репозиторий: https://github.com/DemonIngvi/local-llm-workbench

## Коммиты

```
feat: Add isolated containers for OpenCode and DeepSeek with Task Registry API
- 12 files changed, 1223 insertions(+), 30 deletions(-)
- 23 unit tests passing

docs: Update sprint status and regenerate HTML documentation
- 2 files changed, 47 insertions(+), 19 deletions(-)

feat: Complete production readiness
- Fix Docker image versions with digest
- Add PostgreSQL quotas for LiteLLM
- Add Task Orchestrator with E2E tests
- Add comprehensive documentation
- 30 unit tests passing
```
