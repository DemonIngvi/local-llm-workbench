# Архитектура Local LLM Workbench

## Обзор

Локальный AI workbench для работы с языковыми моделями через единый интерфейс с интеграцией различных агентных фреймворков.

## Компоненты

### 1. LiteLLM Proxy (порт 4100)

**Роль:** Прокси-сервер для управления доступом к моделям LM Studio

**Функции:**
- Агрегирует несколько моделей LM Studio под единым API
- Управляет квотами и лимитами через PostgreSQL
- Предоставляет OpenAI-совместимый API
- Поддерживает виртуальные ключи для разных пользователей

**Конфигурация:**
- Базовый URL: `http://litellm:4000/v1` (внутренний), `http://localhost:4100/v1` (внешний)
- Master key для администрирования: `LITELLM_MASTER_KEY`
- База данных для квот: PostgreSQL 17

**Безопасность:**
- Отдельные виртуальные ключи для OpenCode и DeepSeek
- Ограничение моделей через `allowed_models`
- Лимиты по токенам и бюджету

### 2. LibreChat UI (порт 3200)

**Роль:** Веб-интерфейс для взаимодействия с моделями

**Функции:**
- Чат с моделями через OpenAI-совместимый API
- Управление сессиями и историей
- Настройка параметров моделей

**Интеграция:**
- Подключается к LiteLLM через `http://litellm:4000/v1`
- Использует кастомный endpoint "Local LiteLLM"

### 3. Task Registry API (порт 8080)

**Роль:** HTTP API для управления задачами и их маршрутизации

**Функции:**
- Создание и управление задачами
- Блокировка workspace для предотвращения конфликтов
- Handoff задач между harness (OpenCode ↔ DeepSeek)
- Отслеживание состояния задач

**Endpoints:**
```
GET  /health                    - Проверка работоспособности
GET  /tasks/{id}                - Получение информации о задаче
POST /tasks                     - Создание новой задачи
POST /tasks/{id}/acquire        - Захват задачи harness
POST /tasks/{id}/release        - Освобождение задачи
POST /tasks/{id}/handoff        - Передача задачи другому harness
POST /tasks/{id}/run            - Создание run для OpenCode
```

**База данных:** SQLite (`data/tasks.sqlite3`)

### 4. OpenCode Container

**Роль:** Изолированный контейнер для запуска OpenCode V2

**Изоляция:**
- Непривилегированный пользователь (UID 1001)
- Ограниченные разрешения в `opencode.json`:
  - ✅ Read-only операции (git, ls, cat, find, grep)
  - ✅ Редактирование файлов в workspace
  - ❌ Удаление файлов (rm)
  - ❌ Системные команды (sudo, chmod, chown)
  - ❌ Сетевые запросы (webfetch, websearch)

**Запуск:**
```bash
docker compose --profile on-demand run opencode \
  /usr/local/bin/entrypoint.sh \
  TASK_ID WORKSPACE_PATH MODEL_ID
```

**Интеграция:**
- Получает задачу из Task Registry API
- Работает в изолированном workspace (`/workspace`)
- Записывает результат обратно в реестр

### 5. DeepSeek Container

**Роль:** Изолированный контейнер для DeepSeek Harness

**Изоляция:**
- Непривилегированный пользователь (UID 1001)
- Изолированный профиль `sdk-minimal` без `danger-full-access`
- Ограничения в `cordis.patch.yml`:
  - ✅ Доступ только к `/workspace`
  - ✅ Базовые shell команды с таймаутом 300с
  - ❌ Опасные команды (rm, sudo, docker)
  - ❌ Сетевые утилиты (curl, wget)
  - ❌ Отправка логов в DeepSeek

**Запуск:**
```bash
docker compose --profile on-demand run deepseek \
  /usr/local/bin/dsh-entrypoint.sh \
  TASK_ID WORKSPACE_PATH MODEL_ID
```

**Безопасность:**
- `sandboxMode: workspace-write`
- `session-log-deepseek.enabled: false`

### 6. PostgreSQL (порт 5432)

**Роль:** База данных для LiteLLM квот и метрик

**Конфигурация:**
- База: `litellm`
- Пользователь: `litellm`
- Пароль: `LITELLM_DB_PASSWORD` (из `.env`)

**Функции:**
- Хранение виртуальных ключей
- Учёт использования токенов
- Контроль бюджетов

### 7. MongoDB (порт 27017)

**Роль:** Хранилище данных LibreChat

**Функции:**
- История чатов
- Пользовательские настройки
- Сессии

### 8. Meilisearch (порт 7700)

**Роль:** Поисковый движок для LibreChat

**Функции:**
- Полнотекстовый поиск по истории чатов
- Индексация сообщений

## Сетевая архитектура

```
┌─────────────────────────────────────────────────────────┐
│                    Windows Host                          │
│  ┌──────────────┐                                      │
│  │ LM Studio    │ :1234 (localhost only)                │
│  └──────┬───────┘                                      │
│         │                                               │
│  ┌──────┴───────┐                                      │
│  │ WSL 2        │                                      │
│  │ ┌──────────┐ │                                      │
│  │ │Docker    │ │                                      │
│  │ │┌────────┐│ │    ┌─────────────────────────────┐  │
│  │ ││Frontend││◀┼────┤ LibreChat :3200             │  │
│  │ ││Network ││ │    │ Task Registry :8080         │  │
│  │ │└────────┘│ │    └─────────────────────────────┘  │
│  │ │    │     │ │                │                     │
│  │ │┌────────┐│ │    ┌──────────▼──────────────────┐  │
│  │ ││Backend ││◀┼────┤ LiteLLM :4100               │  │
│  │ ││Network ││ │    │ PostgreSQL :5432            │  │
│  │ │└────────┘│ │    └──────────┬──────────────────┘  │
│  │ └──────────┘ │               │                      │
│  └──────────────┘               │                      │
│                                 │                      │
│  ┌──────────────────────────────▼───────────────────┐  │
│  │ Task Registry SQLite                             │  │
│  │ data/tasks.sqlite3                               │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## Поток данных

### 1. Прямой чат (LibreChat → LiteLLM → LM Studio)

```
User → LibreChat → LiteLLM → LM Studio
                          ↓
                     PostgreSQL (квоты)
```

### 2. Агентная задача (Task Registry → OpenCode)

```
User → Task Registry API (POST /tasks)
       ↓
   Создать задачу в SQLite
       ↓
   POST /tasks/{id}/acquire (захват)
       ↓
   docker compose run opencode TASK_ID /workspace MODEL_ID
       ↓
   OpenCode читает задачу из Task Registry
       ↓
   Выполнение в изолированном контейнере
       ↓
   POST /tasks/{id}/release (освобождение)
```

### 3. Handoff задачи (OpenCode → DeepSeek)

```
OpenCode завершает этап
       ↓
   POST /tasks/{id}/handoff {harness: deepseek, summary: "..."}
       ↓
   Task Registry обновляет задачу
       ↓
   docker compose run deepseek TASK_ID /workspace MODEL_ID
       ↓
   DeepSeek продолжает работу
```

## Безопасность

### Изоляция контейнеров

1. **OpenCode:**
   - Непривилегированный пользователь
   - White-list разрешений
   - Нет доступа к внешним сетям
   - Read-only файловая система (кроме workspace)

2. **DeepSeek:**
   - Непривилегированный пользователь
   - Sandbox режим `workspace-write`
   - Блокировка опасных команд
   - Отключение телеметрии

### Сетевая изоляция

- **Frontend network:** LibreChat, пользовательские запросы
- **Backend network:** Внутренние сервисы (LiteLLM, MongoDB, PostgreSQL)
- **No external access:** Контейнеры не имеют доступа к интернету

### Управление секретами

- Все секреты в `.env` (игнорируется git)
- Отдельные ключи для каждого компонента
- Ротация ключей через `python scripts/setup.py init`

## Масштабирование

### Горизонтальное масштабирование

- LiteLLM: Stateless, можно запускать несколько экземпляров
- Task Registry: Stateless API, можно масштабировать
- OpenCode/DeepSeek: Запускаются по требованию

### Вертикальное масштабирование

- LM Studio: Ограничено ресурсами хоста (RAM, GPU)
- PostgreSQL: Увеличение shared_buffers, work_mem
- MongoDB: Увеличение wiredTiger cache

## Мониторинг

### Метрики LiteLLM

```bash
# Использование токенов
curl -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  http://localhost:4100/v1/models

# Статистика по ключам
curl -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  http://localhost:4100/key/list
```

### Логи

```bash
# Логи всех контейнеров
docker compose logs -f

# Логи конкретного сервиса
docker compose logs -f litellm
docker compose logs -f task-registry
```

## Развертывание

### Production чеклист

- [ ] Зафиксировать версии образов (digest вместо tags)
- [ ] Настроить PostgreSQL с квотами
- [ ] Создать отдельные виртуальные ключи
- [ ] Настроить firewall правила
- [ ] Включить HTTPS для LiteLLM
- [ ] Настроить бэкапы SQLite и PostgreSQL
- [ ] Настроить мониторинг и алертинг
- [ ] Протестировать изоляцию контейнеров
- [ ] Проверить права доступа к файлам
- [ ] Настроить ротацию логов

## Известные ограничения

1. **LM Studio:** Слушает только на localhost, требуется настройка для внешнего доступа
2. **DeepSeek SDK:** Профиль `sdk-minimal` всё ещё имеет ограниченный доступ
3. **OpenCode V2:** Экспериментальный API, может измениться
4. **Task Registry:** Однопользовательский, нет аутентификации API
5. **SQLite:** Не подходит для высоких нагрузок (>100 задач/сек)
