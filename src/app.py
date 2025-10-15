"""Основной модуль приложения."""

import cgi
import http.server
import io
import json
import logging
import os
import re
import uuid
from urllib.parse import urlparse

import database as db
from PIL import Image

STATIC_FILES_DIR = "static"
UPLOAD_DIR = "images"
MAX_FILE_SIZE = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".gif"]
log_dir = "logs"

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

if not os.path.exists(log_dir):
    os.makedirs(log_dir)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(log_dir, "app.log")),
        logging.StreamHandler(),
    ],
)


class ImageHostingHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler for the image hosting server."""

    def _set_headers(self, status_code=200, content_type="text/html"):
        """
        Sets response headers.

        :param status_code: HTTP status code (default: 200)
        :param content_type: Content type header (default: "text/html")
        """
        self.send_response(status_code)
        self.send_header("Content-type", content_type)
        self.end_headers()

    def _get_content_type(self, file_path):
        """
        Returns the content type based on the file extension.

        :param file_path: The path to the file
        :return: The content type
        """
        if file_path.endswith(".html"):
            return "text/html"
        elif file_path.endswith(".css"):
            return "text/css"
        elif file_path.endswith(".js"):
            return "application/javascript"
        elif file_path.endswith((".png", ".jpg", ".jpeg", ".gif")):
            return "image/" + file_path.split(".")[-1]
        else:
            return "application/octet-stream"

    def is_header_multipart(self):
        """
        Checks if the Content-Type header is set to multipart/form-data.

        If the header is not set or does not start with "multipart/form-data",
        sets the response headers to 400 with a JSON response containing
        an error message and returns False.

        :return: True if the header is set to multipart/form-data, False otherwise
        """
        content_type_header = self.headers.get("Content-Type")
        if not content_type_header or not content_type_header.startswith(
            "multipart/form-data"
        ):
            logging.warning("Действие: Ошибка загрузки - некорректный Content-Type.")
            self._set_headers(400, "application/json")
            response = {
                "status": "error",
                "message": "Ожидается multipart/form-data.",
            }
            self.wfile.write(json.dumps(response).encode("utf-8"))
            return False
        return True

    def is_valid_length_request(self):
        """
        Checks if the Content-Length header is set to a valid value.

        If the header is not set or its value is not a positive integer,
        sets the response headers to 411 with a JSON response containing
        an error message and returns False.

        If the value is greater than MAX_FILE_SIZE * 2 (with a small
        reserve for multipart data), sets the response headers to 413
        with a JSON response containing an error message and returns False.

        :return: True if the header is set to a valid value, False otherwise
        """
        try:
            content_length = int(self.headers["Content-Length"])
            if (
                content_length > MAX_FILE_SIZE * 2
            ):  # Небольшой запас на служебную информацию multipart
                logging.warning(
                    f"Действие: Ошибка загрузки - запрос превышает "
                    f"максимальный размер ({content_length} байт)."
                )
                self._set_headers(413, "application/json")  # Payload Too Large
                response = {
                    "status": "error",
                    "message": "Запрос слишком большой.",
                }
                self.wfile.write(json.dumps(response).encode("utf-8"))
                return False

        except (TypeError, ValueError):
            logging.error("Ошибка: Некорректный Content-Length.")
            self._set_headers(411, "application/json")  # Length Required
            response = {
                "status": "error",
                "message": "Некорректный тип Content-Length.",
            }
            self.wfile.write(json.dumps(response).encode("utf-8"))
            return False
        return True

    def is_valid_file_extension(self, file_extension):
        """
        Checks if the file extension is valid.

        If the file extension is not in ALLOWED_EXTENSIONS,
        sets the response headers to 400 with a JSON response
        containing an error message and returns False.

        :param file_extension: The file extension to check
        :return: True if the file extension is valid, False otherwise
        """
        if file_extension not in ALLOWED_EXTENSIONS:
            logging.warning(
                f"Действие: Ошибка загрузки - неподдерживаемый формат файла ({filename})"
            )
            self._set_headers(400, "application/json")
            response = {
                "status": "error",
                "message": f"Неподдерживаемый формат файла. Допустимы: {', '.join(ALLOWED_EXTENSIONS)}",
            }
            self.wfile.write(json.dumps(response).encode("utf-8"))
            return False
        return True

    def is_valid_file_size(self, filename, file_size):
        """
        Checks if the file size is valid.

        If the file size exceeds MAX_FILE_SIZE, sets the response
        headers to 400 with a JSON response containing
        an error message and returns False.

        :param filename: The name of the file to check
        :param file_size: The size of the file to check
        :return: True if the file size is valid, False otherwise
        """
        if file_size > MAX_FILE_SIZE:
            logging.warning(
                f"Действие: Ошибка загрузки - файл превышает максимальный размер ({filename}, {file_size} байт)"
            )
            self._set_headers(400, "application/json")
            response = {
                "status": "error",
                "message": f"Файл превышает максимальный размер {MAX_FILE_SIZE / (1024 * 1024):.0f}MB.",
            }
            self.wfile.write(json.dumps(response).encode("utf-8"))
            return False
        return True

    def do_GET(self):
        """
        Handles a GET request to retrieve a list of images.

        The request path must start with "/images-list".
        The request query must contain a page number in the format "page=<number>".
        If the request is valid, it will return a JSON response containing
        a list of images,
        their details and pagination information.
        If the request is invalid, it will return a 404 response
        with a plain text error message.
        If an exception occurs during the request, it will return a 500 response
        with a JSON response containing the error message.

        :return: None
        """
        parsed_path = urlparse(self.path)
        if parsed_path.path.startswith("/images-list"):
            try:
                page = int(parsed_path.query.split("=")[1]) if parsed_path.query else 1
                offset = (page - 1) * 10
                conn = db.get_connection()
                if not conn:
                    self._set_headers(500, "application/json")
                    response = {
                        "status": "error",
                        "message": "Database connection error",
                    }
                    self.wfile.write(json.dumps(response).encode("utf-8"))
                    return
                cursor = conn.cursor()
                cursor.execute("""SELECT COUNT(*) FROM images;""")
                total_images = cursor.fetchone()[0]
                total_pages = (total_images + 9) // 10
                cursor.execute(
                    """SELECT id, filename, original_name, size, upload_time, file_type
                        FROM images ORDER BY upload_time DESC
                        LIMIT 10 OFFSET %s;""",
                    (offset,),
                )
                images = cursor.fetchall()
                response = {
                    "status": "success",
                    "images": [
                        {
                            "id": image[0],
                            "filename": image[1],
                            "original_name": image[2],
                            "size": image[3],
                            "upload_time": image[4].strftime("%Y-%m-%d %H:%M:%S"),
                            "file_type": image[5],
                        }
                        for image in images
                    ],
                    "pagination": {
                        "total_pages": total_pages,
                        "current_page": page,
                        "has_prev": page > 1,
                        "has_next": page < total_pages,
                    },
                }
                self._set_headers(200, "application/json")
                self.wfile.write(json.dumps(response).encode("utf-8"))
                logging.info(f"Получен список изображений: {total_images} записей.")
            except Exception as e:
                logging.error(f"Ошибка при получении списка изображений: {e}")
                self._set_headers(500, "application/json")
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()
            return
        else:
            logging.warning(
                f"Действие: Неожиданный GET запрос: {self.path}."
                f"Возможно, Nginx не настроен корректно или это ошибка клиента."
            )
            self._set_headers(404, "text/plain")
            self.wfile.write(
                b"404 Not Found (Handled by Nginx for static files,"
                b" or unexpected backend request)"
            )

    def do_POST(self):
        """
        Обрабатывает POST-запрос на /upload.

        Если запрос не является multipart-запросом или файл больше 5МБ,
        то возвращает ошибку.
        Если файл не найден в запросе, то возвращает ошибку.
        Если файл не является изображением (имеет расширение .jpg, .jpeg, .png, .gif)
        или файл больше 5МБ, то возвращает ошибку.
        Если файл успешно загружен, то возвращает успешный ответ с именем файла,
        ссылкой на файл и сообщением об успешной загрузке.
        Если при сохранении файла в базе данных или на диск произошла ошибка,
        то возвращает ошибку.

        :returns: None
        """
        parsed_path = urlparse(self.path)
        if parsed_path.path == "/upload":
            if not (self.is_header_multipart() and self.is_valid_length_request()):
                return
            try:
                fs = cgi.FieldStorage(
                    fp=self.rfile,
                    headers=self.headers,
                    environ={"REQUEST_METHOD": "POST"},
                    keep_blank_values=True,
                )
            except Exception as e:
                logging.error(f"Ошибка при чтении тела запроса: {e}")
                self._set_headers(500, "application/json")
                response = {"status": "error", "message": "Ошибка при чтении запроса."}
                self.wfile.write(json.dumps(response).encode("utf-8"))
                return
            if "file" in fs:
                file_field = fs["file"]
                filename = file_field.filename
                file_data = file_field.file.read()
                if not file_data or not filename:
                    logging.warning(
                        f"Действие: Ошибка загрузки - файл не найден в multipart-запросе."
                    )
                    self._set_headers(400, "application/json")
                    response = {
                        "status": "error",
                        "message": "Файл не найден в запросе.",
                    }
                    self.wfile.write(json.dumps(response).encode("utf-8"))
                    return
                file_size = len(file_data)
                file_extension = os.path.splitext(filename)[1].lower()
                if not (
                    self.is_valid_file_extension(file_extension)
                    and self.is_valid_file_size(filename, file_size)
                ):
                    return

                # Сохранение файла в БД и на диск
                unique_filename = f"{uuid.uuid4().hex}{file_extension}"
                target_path = os.path.join(UPLOAD_DIR, unique_filename)
                file_url = f"/images/{unique_filename}"

                try:
                    conn = db.get_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO images (filename, original_name, size, file_type) VALUES (%s, %s, %s, %s)",
                        (unique_filename, filename, file_size, file_extension),
                    )
                    conn.commit()
                    cursor.close()
                    conn.close()
                    logging.info(
                        f"Изображение '{unique_filename}' успешно сохранено в базе данных."
                    )
                except Exception as e:
                    logging.error(
                        f"Ошибка при сохранении файла '{unique_filename}' в базе данных: {e}"
                    )
                    self._set_headers(500, "application/json")
                    response = {
                        "status": "error",
                        "message": "Произошла ошибка при сохранении файла в базе данных.",
                    }
                    self.wfile.write(json.dumps(response).encode("utf-8"))

                try:
                    image = Image.open(io.BytesIO(file_data))
                    image.save(target_path)
                    logging.info(
                        f"Действие: Изображение '{filename}' (сохранено как '{unique_filename}')"
                        f" успешно загружено. Ссылка: {file_url}"
                    )
                    self._set_headers(200, "application/json")
                    response = {
                        "status": "success",
                        "message": "Файл успешно загружен.",
                        "filename": unique_filename,
                        "url": file_url,
                    }
                    self.wfile.write(json.dumps(response).encode("utf-8"))

                except Exception as e:
                    logging.error(
                        f"Ошибка при сохранении файла '{filename}' в '{target_path}': {e}"
                    )
                    self._set_headers(500, "application/json")
                    response = {
                        "status": "error",
                        "message": "Произошла ошибка при сохранении файла.",
                    }
                    self.wfile.write(json.dumps(response).encode("utf-8"))
        else:
            # Если POST запрос пришел не на /upload, то это неизвестный путь
            logging.warning(f"Действие: Неизвестный POST запрос на: {self.path}")
            self._set_headers(404, "text/plain")
            self.wfile.write(b"404 Not Found")

    def do_DELETE(self):
        """
        Handles a DELETE request to delete an image by its ID.

        The request path must start with "/delete/<image_id>".

        If the request is valid, it will delete the image from the database
        and the file system.
        If the image is not found in the database, it will return
        a 404 response with a JSON response containing an error message.
        If an exception occurs during the request, it will return
        a 500 response with a JSON response containing the error message.

        :return: None
        """
        parsed_path = urlparse(self.path)
        match = re.match(r"/delete/(\d+)", parsed_path.path)
        if match:
            image_id = int(match.group(1))
            try:
                conn = db.get_connection()
                if not conn:
                    self._set_headers(500, "application/json")
                    response = {
                        "status": "error",
                        "message": "Database connection error",
                    }
                    self.wfile.write(json.dumps(response).encode("utf-8"))
                    return
                cursor = conn.cursor()
                cursor.execute("SELECT filename FROM images WHERE id = %s", (image_id,))
                result = cursor.fetchone()
                if result:
                    filename = result[0]
                    file_path = os.path.join(UPLOAD_DIR, filename)
                    cursor.execute("DELETE FROM images WHERE id = %s", (image_id,))
                    conn.commit()
                    cursor.close()
                    conn.close()
                    logging.info(
                        f"Изображение '{filename}' успешно удалено из базы данных."
                    )
                    self._set_headers(200, "application/json")
                    self.wfile.write(json.dumps({"status": "success"}).encode("utf-8"))
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        logging.info(f"Файл '{filename}' успешно удален.")
                    else:
                        logging.warning(f"Файл '{filename}' не был найден.")
                    self._set_headers(200, "application/json")
                else:
                    logging.warning(
                        f"Изображение с id {image_id} не было найдено в базе данных."
                    )
                    self._set_headers(404, "application/json")
                    self.wfile.write(
                        json.dumps(
                            {"status": "error", "message": "Image not found"}
                        ).encode("utf-8")
                    )
            except Exception as e:
                logging.error(f"Ошибка при удалении изображения с id {image_id}: {e}")
                self._set_headers(500, "application/json")
                self.wfile.write(
                    json.dumps(
                        {
                            "status": "error",
                            "message": "Произошла ошибка при удалении изображения.",
                        }
                    ).encode("utf-8")
                )


def run_server(
    server_class=http.server.HTTPServer, handler_class=ImageHostingHandler, port=8000
):
    """
    Runs the HTTP server on the specified port.

    Parameters:
        server_class (http.server.HTTPServer): The class of the HTTP server to use.
        handler_class (ImageHostingHandler): The class of the HTTP request handler to use.
        port (int): The port number to listen on.

    Returns:
        None

    Raises:
        None
    """
    server_address = ("", port)
    httpd = server_class(server_address, handler_class)
    logging.info(f"Сервер запущен на порту {port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    logging.info("Сервер остановлен.")


def initialize_app():
    """
    Инициализирует приложение.

    Проверяет подключение к базе данных PostgreSQL,
    инициализирует таблицу images, если она не существует,
    и возвращает True если инициализация прошла успешно, иначе False.

    :return: bool
    """
    logging.info("Инициализация приложения...")
    if db.test_connection():
        logging.info("Подключение к базе данных установлено.")
        if db.init_database():
            logging.info("База данных инициализирована и готова к использованию.")
        else:
            logging.error("Ошибка при инициализации базы данных: таблица не создана.")
            return False
    else:
        logging.error(
            "Ошибка при подключении к базе данных. "
            "Проверьте конфигурацию в Docker Compose."
        )
        return False
    return True


if __name__ == "__main__":
    if initialize_app():
        run_server()
    else:
        logging.error("Не удалось инициализировать приложение. Сервер не запущен.")
