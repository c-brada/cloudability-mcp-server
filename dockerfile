FROM python:3.12-slim

WORKDIR /app

# Instalar 'uv' para gestionar dependencias rápido
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copiar archivos de dependencias
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

# Copiar el resto del código
COPY . .

# Exponer el puerto que usaremos
EXPOSE 8080

# Comando para ejecutar el servidor en modo HTTP (SSE)
# Nota: Asegúrate de que el script 'run_server.py' soporte el transporte SSE
CMD ["uv", "run", "python", "run_server.py", "--transport", "sse", "--port", "8080"]
