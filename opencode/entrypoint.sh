#!/bin/sh
set -e

# Скрипт-обёртка для интеграции OpenCode с реестром задач
# Принимает параметры: TASK_ID WORKSPACE_PATH MODEL_ID [PROMPT]

TASK_ID=$1
WORKSPACE_PATH=$2
MODEL_ID=$3
PROMPT=$4

if [ -z "$TASK_ID" ] || [ -z "$WORKSPACE_PATH" ] || [ -z "$MODEL_ID" ]; then
    echo "Usage: entrypoint.sh <TASK_ID> <WORKSPACE_PATH> <MODEL_ID> [PROMPT]" >&2
    exit 1
fi

# URL Task Registry API
REGISTRY_URL="${TASK_REGISTRY_URL:-http://task-registry:8080}"

echo "[OpenCode] Starting task $TASK_ID"
echo "[OpenCode] Workspace: $WORKSPACE_PATH"
echo "[OpenCode] Model: $MODEL_ID"

# Получаем информацию о задаче из реестра
echo "[OpenCode] Fetching task info from registry..."
TASK_INFO=$(curl -s -f "$REGISTRY_URL/tasks/$TASK_ID" || echo "")

if [ -z "$TASK_INFO" ]; then
    echo "[OpenCode] ✗ Failed to fetch task info" >&2
    exit 1
fi

echo "[OpenCode] ✓ Task info received"
echo "$TASK_INFO" | python3 -m json.tool 2>/dev/null || echo "$TASK_INFO"

# Переходим в рабочий каталог
cd "$WORKSPACE_PATH"

# Запускаем OpenCode в headless режиме
echo "[OpenCode] Starting OpenCode..."

# Если промпт не указан, используем дефолтный
if [ -z "$PROMPT" ]; then
    PROMPT="Выполните задачу согласно описанию в реестре задач. Задача ID: $TASK_ID"
fi

# Запускаем OpenCode с указанной моделью
opencode run --model "$MODEL_ID" "$PROMPT" || {
    echo "[OpenCode] ✗ OpenCode execution failed" >&2
    exit 1
}

echo "[OpenCode] ✓ Task execution completed"

# Освобождаем задачу в реестре
echo "[OpenCode] Releasing task in registry..."

# Получаем токен из переменной окружения (устанавливается оркестратором)
TASK_TOKEN="${TASK_TOKEN:-}"

if [ -n "$TASK_TOKEN" ]; then
    curl -s -X POST "$REGISTRY_URL/tasks/$TASK_ID/release" \
        -H "Content-Type: application/json" \
        -d "{\"token\": \"$TASK_TOKEN\", \"summary\": \"Task completed by OpenCode\"}" \
        > /dev/null || echo "[OpenCode] ⚠ Failed to release task"
    
    echo "[OpenCode] ✓ Task released"
else
    echo "[OpenCode] ⚠ No task token provided, cannot release task"
fi

echo "[OpenCode] Task $TASK_ID completed successfully"
