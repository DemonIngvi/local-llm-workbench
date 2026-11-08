# Статус

- E1 S1.1–S1.2: ✅ Завершено. Конфигурация создана, запуск работает на обеих ОС.
- E1 S1.3: ✅ Завершено. LibreChat подключён к LiteLLM, прямой чат работает.
- E2 S2.1: ✅ Завершено. Исследованы API OpenCode V2 и DeepSeek Harness, подготовлена конфигурация OpenCode V2 через LiteLLM и экспериментальный HTTP-клиент.
- E2 S2.2: ✅ Завершено. Созданы изолированные контейнеры для OpenCode и DeepSeek с безопасными разрешениями. Добавлен Task Registry API для интеграции.
- E2 S2.3: ✅ Завершено. Прототип SQLite-реестра задач связан с HTTP API. Контейнеры могут получать задачи через REST endpoints.
- E2 S2.4: ✅ Завершено. Документация по безопасности обновлена. Созданы изолированные профили для OpenCode (white-list разрешений) и DeepSeek (sandbox mode без danger-full-access).
- E3 S3.1: ⚠️ В процессе. Добавлена документация по фиксации версий, но версии образов ещё не зафиксированы (используются `latest` теги).
- E3 S3.2: ✅ Завершено. 23 unit-теста пройдены в Windows и WSL, включая mock HTTP API OpenCode, machine state и Task Registry API. Ранее прошёл изолированный Docker smoke-тест LiteLLM с фиктивным сервером.
- E3 S3.3: ✅ Завершено. Отдельные ключи LiteLLM генерируются. Добавлен PostgreSQL для квот. Конфигурация LiteLLM обновлена для работы с базой данных.

## Итого

- **23 unit-теста** (17 старых + 6 новых для Task Registry API)
- **Все тесты проходят** ✅
- **Добавлены изолированные контейнеры** для OpenCode и DeepSeek
- **Task Registry HTTP API** для интеграции контейнеров
- **PostgreSQL** для квот LiteLLM
- **Документация** обновлена (architecture.md, README.md, security-configuration.md)

## Следующие шаги

1. ⚠️ Фиксация версий образов (digest вместо tags)
2. ⚠️ Настройка квот LiteLLM в PostgreSQL
3. ⚠️ Полная интеграция контейнеров через Task Registry API (запуск из LibreChat UI)
4. ⚠️ E2E тестирование с реальным LM Studio
5. ⚠️ Автоматический запуск harness из LibreChat
