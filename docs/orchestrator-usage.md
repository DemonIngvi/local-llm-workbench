# Использование оркестратора задач

Оркестратор задач (`scripts/run_task.py`) автоматизирует выполнение задач через изолированные контейнеры OpenCode и DeepSeek.

## Обзор

Оркестратор выполняет следующий workflow:

1. **Получение задачи** - извлекает информацию о задаче из Task Registry API
2. **Захват задачи** - блокирует задачу для предотвращения конфликтов
3. **Запуск контейнера** - запускает соответствующий контейнер (OpenCode/DeepSeek)
4. **Выполнение** - контейнер выполняет задачу в изолированной среде
5. **Освобождение** - разблокирует задачу и сохраняет результат

## Установка

Убедитесь, что все сервисы запущены:

```bash
python scripts/setup.py start
```

Это запустит:
- LiteLLM (порт 4100)
- LibreChat (порт 3200)
- Task Registry API (порт 8080)
- PostgreSQL (для квот LiteLLM)

## Инициализация базы данных

При первом запуске инициализируйте базу данных LiteLLM с виртуальными ключами:

```bash
# Установите зависимости
pip install psycopg2-binary

# Инициализируйте БД
python scripts/init_litellm_db.py
```

Это создаст:
- Виртуальный ключ для OpenCode (лимит: 1M TPM, 100 RPM, $10 бюджет)
- Виртуальный ключ для DeepSeek (лимит: 500K TPM, 50 RPM, $5 бюджет)

## Создание задачи

### Через API

```bash
curl -X POST http://localhost:8080/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Рефакторинг модуля авторизации",
    "workspace": "D:\\projects\\my-app",
    "harness": "opencode",
    "summary": "Упростить код авторизации, удалить дублирование"
  }'
```

Ответ:
```json
{"task_id": "1"}
```

### Через Python

```python
import urllib.request
import json

data = {
    "title": "Исправить баг в API",
    "workspace": "/path/to/project",
    "harness": "opencode",
    "summary": "Исправить проблему с таймаутом в эндпоинте /api/users"
}

req = urllib.request.Request(
    'http://localhost:8080/tasks',
    data=json.dumps(data).encode(),
    headers={'Content-Type': 'application/json'},
    method='POST'
)

with urllib.request.urlopen(req) as response:
    result = json.loads(response.read())
    task_id = result['task_id']
    print(f"Создана задача: {task_id}")
```

## Выполнение задачи

### Через CLI

```bash
# Выполнить задачу с автоматическим выбором harness
python scripts/run_task.py <task_id>

# Выполнить с кастомным промптом
python scripts/run_task.py <task_id> --prompt "Дополнительные инструкции"

# Указать URL реестра задач (если не localhost)
python scripts/run_task.py <task_id> --registry-url http://custom-host:8080
```

### Примеры

```bash
# Выполнить задачу 1
python scripts/run_task.py 1

# Выполнить задачу 2 с дополнительными инструкциями
python scripts/run_task.py 2 --prompt "Используй типизацию TypeScript"

# Выполнить задачу на удалённом сервере
python scripts/run_task.py 3 --registry-url http://192.168.1.100:8080
```

### Через Python

```python
from scripts.run_task import TaskOrchestrator

orchestrator = TaskOrchestrator(registry_url='http://localhost:8080')

# Выполнить задачу
success = orchestrator.execute_task(task_id='1')

if success:
    print("Задача выполнена успешно")
else:
    print("Задача завершилась с ошибкой")
```

## Проверка статуса задачи

```bash
# Получить информацию о задаче
curl http://localhost:8080/tasks/<task_id>

# Пример ответа
{
  "id": "1",
  "title": "Рефакторинг модуля авторизации",
  "workspace": "D:\\projects\\my-app",
  "harness": "opencode",
  "summary": "Задача выполнена успешно. Удалено 150 строк дублирующегося кода.",
  "locked": false,
  "lock_token": null,
  "created_at": 1699459200
}
```

## Ручное управление задачами

### Захват задачи

```bash
curl -X POST http://localhost:8080/tasks/<task_id>/acquire \
  -H "Content-Type: application/json" \
  -d '{"harness": "opencode"}'

# Ответ: {"token": "abc123..."}
```

### Освобождение задачи

```bash
curl -X POST http://localhost:8080/tasks/<task_id>/release \
  -H "Content-Type: application/json" \
  -d '{
    "token": "abc123...",
    "summary": "Задача выполнена. Изменены файлы: auth.py, utils.py"
  }'
```

### Передача задачи другому harness

```bash
# Передать от OpenCode к DeepSeek
curl -X POST http://localhost:8080/tasks/<task_id>/handoff \
  -H "Content-Type: application/json" \
  -d '{
    "to_harness": "deepseek",
    "reason": "OpenCode завершил первый этап, теперь нужна оптимизация"
  }'
```

## Мониторинг

### Просмотр логов контейнера

```bash
# Логи OpenCode контейнера
docker compose logs -f opencode

# Логи DeepSeek контейнера
docker compose logs -f deepseek

# Логи Task Registry
docker compose logs -f task-registry
```

### Проверка здоровья сервисов

```bash
# Task Registry API
curl http://localhost:8080/health

# LiteLLM
curl http://localhost:4100/health

# LibreChat
curl http://localhost:3200/health
```

### Использование квот LiteLLM

```bash
# Проверить использование ключа
curl -H "Authorization: Bearer $LITELLM_OPENCODE_KEY" \
  http://localhost:4100/key/info

# Список всех ключей
curl -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  http://localhost:4100/key/list
```

## Настройка квот

Квоты настраиваются в `scripts/init_litellm_db.py`:

```python
# OpenCode ключ
create_virtual_key(
    key_name="opencode_key",
    token=os.environ.get('LITELLM_OPENCODE_KEY'),
    allowed_models=[],  # Все модели
    tpm_limit=1000000,  # 1M токенов/мин
    rpm_limit=100,      # 100 запросов/мин
    max_budget=10.0     # $10 бюджет
)

# DeepSeek ключ
create_virtual_key(
    key_name="deepseek_key",
    token=os.environ.get('LITELLM_DEEPSEEK_KEY'),
    allowed_models=[],
    tpm_limit=500000,   # 500K токенов/мин
    rpm_limit=50,       # 50 запросов/мин
    max_budget=5.0      # $5 бюджет
)
```

## Troubleshooting

### Ошибка: "Task already locked"

Задача уже выполняется другим процессом. Дождитесь завершения или вручную освободите:

```bash
# Получить информацию о задаче
curl http://localhost:8080/tasks/<task_id>

# Если locked=true, можно принудительно освободить через БД
# (требует прямого доступа к SQLite)
```

### Ошибка: "Container execution failed"

Проверьте логи контейнера:

```bash
docker compose logs opencode
docker compose logs deepseek
```

Частые причины:
- Недостаточно памяти для модели
- Ошибка в промпте
- Проблемы с доступом к workspace

### Ошибка: "Task Registry API not available"

Убедитесь, что Task Registry запущен:

```bash
docker compose ps task-registry
docker compose logs task-registry
```

### Ошибка: "LM Studio not accessible"

LM Studio должен слушать на всех интерфейсах:

1. Откройте LM Studio
2. Developer → Local Server
3. Измените Host: `localhost` → `0.0.0.0`
4. Перезапустите сервер

Подробнее: [docs/lm-studio-network-setup.md](lm-studio-network-setup.md)

## Безопасность

### Изоляция контейнеров

- **OpenCode**: white-list разрешений, нет доступа к внешним сетям
- **DeepSeek**: sandbox mode, заблокированы опасные команды
- **Workspace**: монтируется только для чтения/записи в указанную директорию

### Сетевая изоляция

- Контейнеры не имеют доступа к интернету
- Доступ только к внутренним сервисам (LiteLLM, Task Registry)
- Используются отдельные сети: `frontend` и `backend`

### Управление секретами

Все секреты хранятся в `.env` файле:
- `LITELLM_MASTER_KEY` - административный ключ
- `LITELLM_OPENCODE_KEY` - ключ для OpenCode
- `LITELLM_DEEPSEEK_KEY` - ключ для DeepSeek
- `OPENCODE_SERVER_PASSWORD` - пароль OpenCode

**Важно**: никогда не коммитьте `.env` в git!

## Примеры использования

### Пример 1: Простая задача

```bash
# Создать задачу
curl -X POST http://localhost:8080/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Добавить тесты",
    "workspace": "D:\\projects\\my-app",
    "harness": "opencode",
    "summary": "Написать unit-тесты для модуля utils.py"
  }'

# Выполнить задачу
python scripts/run_task.py 1
```

### Пример 2: Передача между harness

```bash
# Создать задачу для OpenCode
curl -X POST http://localhost:8080/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Оптимизация производительности",
    "workspace": "D:\\projects\\my-app",
    "harness": "opencode",
    "summary": "Найти узкие места в коде"
  }'

# Выполнить первый этап
python scripts/run_task.py 1

# Передать DeepSeek для оптимизации
curl -X POST http://localhost:8080/tasks/1/handoff \
  -H "Content-Type: application/json" \
  -d '{
    "to_harness": "deepseek",
    "reason": "OpenCode нашёл проблемы, теперь нужна оптимизация"
  }'

# Выполнить второй этап
python scripts/run_task.py 1
```

### Пример 3: Массовое выполнение

```python
from scripts.run_task import TaskOrchestrator

orchestrator = TaskOrchestrator()

# Список задач
tasks = ['1', '2', '3', '4', '5']

# Выполнить все задачи
results = {}
for task_id in tasks:
    success = orchestrator.execute_task(task_id)
    results[task_id] = success

# Вывести результаты
for task_id, success in results.items():
    status = "✓" if success else "✗"
    print(f"{status} Задача {task_id}")
```

## Дополнительные ресурсы

- [Архитектура](architecture.md) - детальная архитектура системы
- [Безопасность](security-configuration.md) - конфигурация безопасности
- [Реестр задач](task-handoff.md) - управление задачами
- [OpenCode интеграция](opencode-integration.md) - интеграция OpenCode V2
