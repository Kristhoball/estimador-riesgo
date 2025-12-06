FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 1. Instalar dependencias y Caddy
RUN apt-get update && apt-get install -y \
    curl unzip util-linux \
    debian-keyring debian-archive-keyring apt-transport-https \
    && curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg \
    && curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list \
    && apt-get update && apt-get install -y caddy \
    && rm -rf /var/lib/apt/lists/*

# 2. Usuario
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH
WORKDIR $HOME/app

# 3. Archivos
COPY --chown=user requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY --chown=user . .

# 4. Limpieza y Script de arranque
RUN rm -f .gitignore requirements.txt
# Damos permiso de ejecución al script (Importante)
RUN chmod +x start.sh

# 5. Inicializar
RUN reflex init

# 6. URL Pública
ENV REFLEX_API_URL=https://estimador-riesgo.zeabur.app

# 7. Construir Web
RUN reflex export --frontend-only --no-zip

# 8. Caddyfile (CONFIGURACIÓN ESTÁNDAR SPA)
# Esta configuración es más segura para evitar conflictos de rutas
RUN echo "{\n\
    auto_https off\n\
}\n\
\n\
:8080 {\n\
    # Compresión para que cargue rápido\n\
    encode gzip\n\
    \n\
    # Rutas del Backend\n\
    handle /_event/* {\n\
        reverse_proxy 127.0.0.1:8000\n\
    }\n\
    handle /ping {\n\
        reverse_proxy 127.0.0.1:8000\n\
    }\n\
    \n\
    # Ruta del Frontend (Todo lo demás)\n\
    handle {\n\
        root * /home/user/app/.web/_static\n\
        try_files {path} {path}/ /index.html\n\
        file_server\n\
    }\n\
}" > Caddyfile

# 9. Ejecutar script
CMD ["./start.sh"]