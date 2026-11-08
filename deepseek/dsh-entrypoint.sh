#!/bin/sh
set -e

# Скрипт-обёртка для интеграции DeepSeek с реестром задач
# Принимает параметры: TASK_ID WORKSPACE_PATH MODEL_ID [PROMPT]

TASK_ID=$1
WORKSPACE_PATH=$2
MODEL_ID=$3
PROMPT=$4

if [ -z "$TASK_ID" ] || [ -z "$WORKSPACE_PATH" ] || [ -z "$MODEL_ID" ]; then
    echo "Usage: dsh-entrypoint.sh <TASK_ID> <WORKSPACE_PATH> <MODEL_ID> [PROMPT]" >&2
    exit 1
fi

# URL Task Registry API
REGISTRY_URL="${TASK_REGISTRY_URL:-http://task-registry:8080}"

echo "[DeepSeek] Starting task $TASK_ID"
echo "[DeepSeek] Workspace: $WORKSPACE_PATH"
echo "[DeepSeek] Model: $MODEL_ID"

# Получаем информацию о задаче из реестра
echo "[DeepSeek] Fetching task info from registry..."
TASK_INFO=$(curl -s -f "$REGISTRY_URL/tasks/$TASK_ID" || echo "")

if [ -z "$TASK_INFO" ]; then
    echo "[DeepSeek] ✗ Failed to fetch task info" >&2
    exit 1
fi

echo "[DeepSeek] ✓ Task info received"
echo "$TASK_INFO" | python3 -m json.tool 2>/dev/null || echo "$TASK_INFO"

# Переходим в рабочий каталог
cd "$WORKSPACE_PATH"

# Если промпт не указан, используем дефолтный
if [ -z "$PROMPT" ]; then
    PROMPT="Выполните задачу согласно описанию в реестре задач. Задача ID: $TASK_ID"
fi

# Запускаем DeepSeek в headless режиме
echo "[DeepSeek] Starting DeepSeek Harness..."

dsh --profile sdk-minimal --headless "$PROMPT" || {
    echo "[DeepSeek] ✗ DeepSeek execution failed" >&2
    exit 1
}

echo "[DeepSeek] ✓ Task execution completed"

# Освобождаем задачу в реестре
echo "[DeepSeek] Releasing task in registry..."

# Получаем токен из переменной окружения (устанавливается оркестратором)
TASK_TOKEN="${TASK_TOKEN:-}"

if [ -n "$TASK_TOKEN" ]; then
    curl -s -X POST "$REGISTRY_URL/tasks/$TASK_ID/release" \
        -H "Content-Type: application/json" \
        -d "{\"token\": \"$TASK_TOKEN\", \"summary\": \"Task completed by DeepSeek\"}" \
        > /dev/null || echo "[DeepSeek] ⚠ Failed to release task"
    
    echo "[DeepSeek] ✓ Task released"
else
    echo "[DeepSeek] ⚠ No task token provided, cannot release task"
fi

echo "[DeepSeek] Task $TASK_ID completed successfully"
