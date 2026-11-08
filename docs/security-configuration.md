# Конфигурация безопасности и ограничения

## Зафиксированные версии

`compose.yaml` использует плавающие теги `main-stable` и `latest`. Для production зафиксируйте точные digest или версии:

```bash
# Получите текущий digest
docker pull ghcr.io/berriai/litellm:main-stable
docker inspect --format='{{index .RepoDigests 0}}' ghcr.io/berriai/litellm:main-stable

# Обновите compose.yaml
image: ghcr.io/berriai/litellm@sha256:...
```

После фиксации версий проверяйте обновление в изолированной среде перед развёртыванием.

## Отдельные ключи LiteLLM

После первого запуска в `.env` созданы:
- `LITELLM_MASTER_KEY` — административный ключ для управления LiteLLM
- `LITELLM_OPENCODE_KEY` — для OpenCode (ограниченный, с квотами)
- `LITELLM_DEEPSEEK_KEY` — для DeepSeek (ограниченный, с квотами)

Для включения квот и ограничения моделей требуется база данных LiteLLM и настройка `user_api_key_auth`. Без этого все ключи имеют одинаковый доступ. Добавьте в `litellm.json`:

```json
{
  "general_settings": {
    "master_key": "os.environ/LITELLM_MASTER_KEY",
    "database_url": "postgresql://...",
    "enable_accounting": true
  },
  "litellm_settings": {
    "key_generation": {
      "allowed_models": ["model-id"],
      "max_budget": 10.0,
      "tpm_limit": 100000
    }
  }
}
```

До настройки базы данных **не используйте ограниченный ключ в production** — он не ограничен.

## Безопасность OpenCode

`generated/opencode.json` содержит политику полного запрета:

```json
{
  "permissions": [{"action": "*", "resource": "*", "effect": "deny"}]
}
```

Это предотвращает случайное выполнение инструментов. Для реальной работы разрешите необходимые действия явно:

```json
{
  "permissions": [
    {"action": "read", "resource": "*", "effect": "allow"},
    {"action": "shell", "resource": "git *", "effect": "allow"},
    {"action": "shell", "resource": "pytest *", "effect": "allow"},
    {"action": "edit", "resource": "/workspace/*", "effect": "allow"},
    {"action": "shell", "resource": "rm *", "effect": "deny"},
    {"action": "shell", "resource": "sudo *", "effect": "deny"}
  ]
}
```

Правила применяются в порядке объявления; последнее совпадение побеждает. Проверяйте эффективную политику через `/api/permission/saved` перед запуском задач с реальными файлами.

## Критические ограничения DeepSeek

**Официальный SDK DeepSeek (`sdk-minimal`) использует `danger-full-access`** — это означает:

1. **Агент может модифицировать любой файл**, доступный процессу
2. **Агент может выполнять любые команды** в оболочке
3. **События журнала отправляются в DeepSeek** при использовании их API

Нельзя подключать этот профиль к пользовательским файлам как к песочнице. Требования для безопасного использования:

### Обязательные меры

1. **Изолированный контейнер** с ограниченным workspace:
   ```dockerfile
   FROM node:22-alpine
   RUN npm install -g @deepseek-ai/dsh
   WORKDIR /workspace
   RUN adduser -D -h /home/dsh dsh
   USER dsh
   ```

2. **Отдельный профиль без `danger-full-access`**:
   ```yaml
   # cordis.patch.yml
   - id: bash
     config:
       allowedDirectories: ["/workspace"]
       blockedCommands: ["rm", "sudo", "docker"]
   ```

3. **Отключение отправки журнала**:
   ```yaml
   # cordis.patch.yml
   - id: session-log-deepseek
     config:
       enabled: false
   ```

4. **Сетевые ограничения**: только к LiteLLM и необходимым ресурсам

5. **Ручная проверка** перед каждой задачей: что агент может читать/писать/выполнять

### Альтернативы

- Используйте OpenCode с явными правилами разрешений
- Разработайте собственный профиль DSH с sandbox-политикой
- Используйте виртуальную машину с ограниченным доступом

## Текущее состояние

Прототип **не включает**:
- Автоматическую изоляцию DeepSeek
- Квоты LiteLLM без базы данных
- Полную интеграцию harness в LibreChat
- Реальное E2E тестирование с LM Studio

Для production требуется:
1. Фиксация версий всех образов
2. Настройка базы данных LiteLLM с квотами
3. Разработка изолированного профиля DeepSeek
4. Integration-тесты с реальным LM Studio
5. Ревью политики разрешений OpenCode
6. Мониторинг и аудит выполнения задач
