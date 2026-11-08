# Подключение и безопасность

## Получение моделей

LM Studio предоставляет `GET /v1/models` (OpenAI-совместимый формат `data[].id`) и более подробный нативный `GET /api/v1/models`: https://lmstudio.ai/docs/developer/openai-compat/models , https://lmstudio.ai/docs/developer/rest/list . Скрипт использует первый формат, создавая по записи LiteLLM на каждый ID. При включённом JIT список содержит скачанные модели; при выключенном — только загруженные: https://lmstudio.ai/docs/developer/core/headless . Список может включать embedding-модели, которые не являются чат-моделями; выберите подходящую вручную. Автосинхронизация не работает в фоне: после изменения списка выполняйте `refresh`.

## Два адреса

После `init` можно изменить `.env`:

- `LM_STUDIO_HOST_URL`: адрес `/v1`, доступный процессу запуска на Windows или Linux; по умолчанию `http://localhost:1234/v1`.
- `LM_STUDIO_CONTAINER_URL`: адрес `/v1`, доступный контейнеру LiteLLM; по умолчанию `http://host.docker.internal:1234/v1`.
- `LM_STUDIO_API_KEY`: токен LM Studio, либо `not-needed`, если авторизация отключена. Один и тот же ключ используется для обнаружения и inference.

При запуске Linux Docker Engine на WSL и LM Studio на Windows адрес gateway контейнера может указывать на WSL, а не Windows. Укажите в обоих URL адрес Windows, реально достижимый из соответствующего пространства имён; проверьте маршрутизацию и firewall. Docker Desktop и обычный Docker Engine устроены по-разному; `localhost` контейнера — не Windows-хост. Порт LM Studio должен слушать интерфейс, доступный клиентам. Доступ на LAN-интерфейсе потенциально открывает его другим устройствам: ограничьте firewall доверенными адресами и включите токен; не публикуйте сервис в интернет. Даже с токеном обычный HTTP не шифрует трафик. Документация: https://lmstudio.ai/docs/developer/core/server и https://docs.docker.com/desktop/features/networking/ .

LiteLLM и LibreChat публикуются только на loopback. LiteLLM защищён сгенерированным master key; LibreChat использует его внутри приватной сети как компромисс MVP. Файл `.env` содержит секреты: не публикуйте его и ограничьте доступ; на Windows права наследуются от каталога. После регистрации выключите `ALLOW_REGISTRATION` в `.env` и запустите `refresh`. Изоляция контейнеров не является надёжной песочницей для недоверенного кода; Docker socket и рабочая папка намеренно не монтируются к агентам.

Диагностика: проверьте `/v1/models` на хосте с Bearer-токеном, `status`, затем `logs`. Успешный список на хосте не доказывает доступ из контейнера. Ошибки скачивания/загрузки моделей и неподдерживаемые параметры зависят от LM Studio и выбранной модели. Конфигурация LiteLLM: https://docs.litellm.ai/docs/providers/openai_compatible ; LibreChat: https://www.librechat.ai/docs/quick_start/custom_endpoints .
