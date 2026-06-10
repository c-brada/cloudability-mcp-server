FROM python:3.14-alpine

RUN apk upgrade --no-cache \
    && addgroup -g 1000 app \
    && adduser -D -u 1000 -G app -s /sbin/nologin app

WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen \
    && chown -R app:app /app

COPY --chown=app:app . .

USER app

EXPOSE 8080
CMD ["uv", "run", "python", "main.py", "--transport", "sse", "--port", "8080"]
