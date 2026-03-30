#!/bin/bash

# 1. Пути
PROJECT_DIR="/root/polygate_project"
ENV_FILE="$PROJECT_DIR/.env"

# 2. Загружаем переменные напрямую (более надежный способ для bash)
if [ -f "$ENV_FILE" ]; then
    # Читаем файл, убираем возможные \r (Windows-формат) и экспортируем
    export $(cat "$ENV_FILE" | sed 's/\r$//' | grep -v '^#' | xargs)
else
    echo "❌ Ошибка: Файл .env не найден!"
    exit 1
fi

# 3. Проверка переменных (если пустые - выходим)
if [ -z "$TG_TOKEN" ] || [ -z "$ADMIN_ID" ]; then
    echo "❌ Ошибка: TG_TOKEN или ADMIN_ID не найдены в .env"
    exit 1
fi

# 4. Настройки
DATE=$(date +"%Y-%m-%d_%H-%M")
BACKUP_PATH="$PROJECT_DIR/backup_$DATE.sql"
CAPTION="📦 Резервная копия БД: $DATE"

# 5. Создаем дамп
sudo -u postgres pg_dump polygate > "$BACKUP_PATH"

# 6. Отправляем в Telegram (используем ключи -F для безопасности параметров)
curl -v -F document=@"$BACKUP_PATH" \
     -F chat_id="$ADMIN_ID" \
     -F caption="$CAPTION" \
     "https://api.telegram.org/bot$TG_TOKEN/sendDocument"

# 7. Удаляем временный файл
rm "$BACKUP_PATH"
