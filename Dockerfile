FROM python:3.13-slim as builder

WORKDIR /app

ENV PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_NO_CACHE_DIR=off \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1   

RUN pip install "poetry==2.1.2"
RUN groupadd --system service && useradd --system -g service api

COPY poetry.lock pyproject.toml ./
RUN poetry config virtualenvs.create false \
    && poetry install --no-ansi --no-root


FROM python:3.13-slim

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages

COPY app.py .

COPY static/ ./static/

EXPOSE 8000

CMD ["python", "app.py"]