#!/bin/bash

BACKUP_DIR="./backups"
CONTAINER_NAME="image-hosting-frontend-db-1"
DB_NAME="images_db"
DB_USER="postgres"

if [ $# -ne 1 ]; then
    echo "Usage: $0 <backup_file>"
    echo "Example: $0 backups/backup_2024-06-01_123456.sql"
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file '$BACKUP_FILE' does not exist"
    exit 1
fi

# Проверяем существование контейнера
if ! docker ps | grep -q "$CONTAINER_NAME"; then
    echo "Error: Container $CONTAINER_NAME is not running"
    exit 1
fi

echo "Restoring database '$DB_NAME' from backup file '$BACKUP_FILE'..."

# Восстанавливаем базу
cat "$BACKUP_FILE" | docker exec -i $CONTAINER_NAME psql -U $DB_USER -d $DB_NAME

if [ $? -eq 0 ]; then
    echo "Database successfully restored from $BACKUP_FILE"
else
    echo "Error during database restore"
    exit 1
fi