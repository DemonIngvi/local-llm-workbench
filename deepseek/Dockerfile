# DeepSeek Harness с изолированным профилем
FROM node:22-alpine

# Устанавливаем Python для SDK
RUN apk add --no-cache python3 py3-pip git bash curl

# Устанавливаем DeepSeek Harness
RUN npm install -g @deepseek-ai/dsh@latest

# Создаём пользователя с ограниченными правами
RUN addgroup -g 1001 dsh && \
    adduser -u 1001 -G dsh -s /bin/sh -D dsh

# Создаём домашнюю директорию для DSH
RUN mkdir -p /home/dsh/.dsh && chown -R dsh:dsh /home/dsh

# Копируем изолированный профиль
COPY --chown=dsh:dsh cordis.patch.yml /home/dsh/.dsh/profiles/sdk-minimal/cordis.patch.yml
COPY --chown=dsh:dsh dsh-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/dsh-entrypoint.sh

# Создаём рабочую директорию
RUN mkdir -p /workspace && chown dsh:dsh /workspace
WORKDIR /workspace

# Переключаемся на непривилегированного пользователя
USER dsh

ENV DSH_HOME=/home/dsh/.dsh

ENTRYPOINT ["/usr/local/bin/dsh-entrypoint.sh"]
