# Настройка LM Studio для работы с LibreChat

## Проблема

LM Studio по умолчанию слушает только на `localhost` (127.0.0.1), что делает его недоступным из Docker контейнеров в WSL.

## Решение

Нужно изменить настройки LM Studio, чтобы он слушал на всех интерфейсах (0.0.0.0):

### Вариант 1: Через UI (рекомендуется)

1. Откройте LM Studio
2. Перейдите в **Developer** → **Local Server** (или Server)
3. В настройках сервера найдите **Host** или **Bind Address**
4. Измените с `localhost` или `127.0.0.1` на `0.0.0.0`
5. Перезапустите сервер (кнопка Stop → Start)

### Вариант 2: Через CLI (если используете CLI версию)

```bash
lms server start --host 0.0.0.0 --port 1234
```

## Проверка

После изменения настроек проверьте, что LM Studio слушает на всех интерфейсах:

```powershell
netstat -ano | findstr ":1234"
```

Должно показать `0.0.0.0:1234` вместо `127.0.0.1:1234`.

## Альтернатива: Port Proxy (требует прав администратора)

Если не можете изменить настройки LM Studio, можно использовать Windows port proxy:

```powershell
# Запустите PowerShell от имени администратора
netsh interface portproxy add v4tov4 listenport=1234 listenaddress=0.0.0.0 connectport=1234 connectaddress=127.0.0.1

# Проверить
netsh interface portproxy show all

# Удалить (когда не нужно)
netsh interface portproxy delete v4tov4 listenport=1234 listenaddress=0.0.0.0
```

## После настройки

1. Убедитесь, что модель `qwen2.5-coder-7b-instruct` загружена в LM Studio
2. Запустите LibreChat:
   ```bash
   wsl -d Ubuntu -- bash -c "cd /mnt/d/local-llm-workbench && docker compose up -d"
   ```
3. Откройте http://localhost:3200
4. Зарегистрируйтесь и начните чат
