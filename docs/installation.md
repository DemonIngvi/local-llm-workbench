# Установка зависимостей

## Windows 10/11

1. В PowerShell администратора: `wsl --install`; перезагрузите ПК и создайте пользователя Linux. Документация и требования версий: https://learn.microsoft.com/windows/wsl/install . Проверка: `wsl --status`, `wsl -l -v` (дистрибутив версии 2).
2. Установите Docker Desktop: https://docs.docker.com/desktop/setup/install/windows-install/ . Включите WSL 2 backend и интеграцию с дистрибутивом, если запускаете скрипт из WSL. Либо используйте Docker Engine и Compose, установленные непосредственно в Ubuntu WSL. Проверьте `docker version` и `docker compose version` в том окружении, где доступен daemon. Если `docker` отсутствует в Windows PATH, `start.cmd` автоматически передаст запуск в WSL-дистрибутив по умолчанию; там должны быть Docker, Compose и Python.
3. Установите Python 3: https://www.python.org/downloads/windows/ ; включите PATH, проверьте `python --version`. В WSL нужен отдельный `python3`.
4. LM Studio **не устанавливается этим проектом**. Официальные инструкции: https://lmstudio.ai/docs/app ; сервер: https://lmstudio.ai/docs/developer/core/server . Модель и размер контекста выбирайте по доступной RAM/VRAM.
5. Скопируйте каталог проекта на диск; запускайте `start.cmd` из Windows либо `bash start.sh` из WSL. Если из WSL Windows localhost недоступен, используйте доступный из WSL IP Windows-хоста в `LM_STUDIO_HOST_URL`, и отдельно проверьте доступ контейнера.

## Linux

1. Установите Docker Engine и Compose plugin по инструкциям для вашего дистрибутива: https://docs.docker.com/engine/install/ и https://docs.docker.com/compose/install/linux/ . Проверьте `docker compose version` и доступ к Docker без sudo либо запускайте скрипт с корректно настроенными правами. Доступ к Docker эквивалентен практически root-доступу.
2. Установите Python 3 через пакетный менеджер, проверьте `python3 --version`.
3. Можно использовать Linux-версию LM Studio или официальный headless llmster: https://lmstudio.ai/docs/developer/core/headless . Проект не устанавливает и не запускает его. Для llmster после отдельной установки: `lms daemon up`, `lms server start`; загрузите модель или включите JIT. Используйте документацию подходящей версии.
4. `bash start.sh`. На Linux `host.docker.internal` сопоставлен с Docker host gateway; сервис на одном только 127.0.0.1 хоста обычно недоступен контейнеру. См. [connection.md](connection.md).

## Компоненты и библиотеки

LibreChat, LiteLLM, MongoDB и Meilisearch устанавливаются как образы при `docker compose up`; вручную устанавливать их в систему не требуется. Python использует только стандартную библиотеку. LibreChat сохраняет историю в MongoDB и использует Meilisearch для поиска. RAG, вложения с извлечением и OpenCode/DeepSeek в текущий срез не входят. Для установки агентов см. официальные источники: https://opencode.ai/docs/ и https://github.com/deepseek-ai/deepseek-harness ; не устанавливайте их на хост автоматически ради этого проекта.
