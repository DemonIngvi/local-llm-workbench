#!/bin/sh
set -e

# Скрипт-обёртка для интеграции OpenCode с реестром задач
# Принимает параметры: TASK_ID WORKSPACE_PATH MODEL_ID
# Читает задачу из реестра, запускает OpenCode, записывает результат

TASK_ID=$1
WORKSPACE_PATH=$2
MODEL_ID=$3

if [ -z "$TASK_ID" ] || [ -z "$WORKSPACE_PATH" ] || [ -z "$MODEL_ID" ]; then
    echo "Usage: entrypoint.sh <TASK_ID> <WORKSPACE_PATH> <MODEL_ID>" >&2
    exit 1
fi

# Переходим в рабочий каталог
cd "$WORKSPACE_PATH"

# Получаем информацию о задаче из реестра (через HTTP API реестра)
# TODO: Интеграция с реестром задач через HTTP endpoint
echo "Starting OpenCode for task $TASK_ID in $WORKSPACE_PATH with model $MODEL_ID"

# Запускаем OpenCode в headless режиме с указанной моделью
opencode --headless --model "$MODEL_ID" "$@"

# После завершения записываем результат в реестр
# TODO: Вызов HTTP endpoint реестра для обновления статуса задачи
echo "Task $TASK_ID completed"
