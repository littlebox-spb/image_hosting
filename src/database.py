import psycopg2
import os
import logging

DB_CONFIG = {
    "user": os.environ.get("DB_USER", "postgres"),
    "password": os.environ.get("DB_PASS", "password"),
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": os.environ.get("DB_PORT", 5432),
    "database": os.environ.get("DB_NAME", "image_db"),
}


def get_connection():
    """
    Returns a connection to the PostgreSQL database.

    Returns:
        conn (psycopg2.extensions.connection): Connection to the database.

    Raises:
        psycopg2.Error: If there is an error connecting to the database.
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except psycopg2.Error as e:
        logging.error(f"Ошибка подключения к базе данных: {e}")
        return None


def test_connection():
    """
    Тестирует подключение к базе данных PostgreSQL.

    Возвращает:
        bool: True если подключение успешно, иначе False.

    Raises:
        psycopg2.Error: Если возникла ошибка подключения к базе данных.
    """
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            logging.info(
                f"Подключение к базе данных PostgreSQL успешно. Версия: {version[0]}"
            )
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            logging.error(f"Ошибка при тестировании подключения к базе данных: {e}")
            return False
    return False


def init_database():
    """
    Инициализирует таблицу images в базе данных PostgreSQL.

    Если таблица images не существует, то она будет создана.
    В противном случае, функция просто возвращает True.

    Возвращает:
        bool: True если таблица images создана успешно, иначе False.

    Raises:
        psycopg2.Error: Если возникла ошибка подключения к базе данных.
    """
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS images (
                    id SERIAL PRIMARY KEY,
                    filename TEXT NOT NULL,
                    original_name TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    file_type TEXT NOT NULL
                );
            """
            )
            conn.commit()
            logging.info("Таблица images создана успешно.")
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            logging.error(f"Ошибка при инициализации базы данных: {e}")
            return False
    return False
