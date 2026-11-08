# OpenCode V2 изолированный контейнер с интеграцией в реестр задач
FROM node:20-alpine

# Устанавливаем зависимости
RUN apk add --no-cache git python3 bash curl

# Создаём пользователя с ограниченными правами
RUN addgroup -g 1001 opencode && \
    adduser -u 1001 -G opencode -s /bin/sh -D opencode

# Устанавливаем OpenCode V2
RUN npm install -g @opencode-ai/opencode@latest

# Создаём рабочую директорию с правильными правами
RUN mkdir -p /workspace && chown opencode:opencode /workspace
WORKDIR /workspace

# Копируем скрипт-обёртку для интеграции с реестром задач
COPY --chown=opencode:opencode entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/entrypoint.sh

# Копируем конфигурацию с безопасными разрешениями
COPY --chown=opencode:opencode opencode.json /home/opencode/.config/opencode/opencode.json

# Переключаемся на непривилегированного пользователя
USER opencode

# По умолчанию запускаем OpenCode в headless режиме
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["--headless"]
