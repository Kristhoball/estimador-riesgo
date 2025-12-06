# 1. Imagen base
FROM python:3.11-slim

# 2. Configuración
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Instalar dependencias
RUN apt-get update && apt-get install -y \
    curl unzip util-linux \
    debian-keyring debian-archive-keyring apt-transport-https \
    && curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg \
    && curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list \
    && apt-get update && apt-get install -y caddy \
    && rm -rf /var/lib/apt/lists/*

# 4. Usuario
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH
WORKDIR $HOME/app

# 5. Copiar archivos
COPY --chown=user requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY --chown=user . .

# 6. Limpieza de permisos
RUN rm -f .gitignore requirements.txt

# 7. Inicializar
RUN reflex init

# 8. URL Pública (HTTPS)
ENV REFLEX_API_URL=https://estimador-riesgo.zeabur.app

# 9. Construir la Web
RUN reflex export --frontend-only --no-zip

# 10. Configuración de Caddy (SIMPLIFICADA Y ROBUSTA)
# Aquí estaba el problema. Ahora definimos la raíz globalmente.
RUN echo "{\n\
    auto_https off\n\
}\n\
\n\
:8080 {\n\
    bind 0.0.0.0\n\
    \n\
    # Definimos dónde están los archivos de la web\n\
    root * /home/user/app/.web/_static\n\
    \n\
    # Habilitamos el servidor de archivos\n\
    file_server\n\
    \n\
    # Reglas para el Backend (Python)\n\
    handle /_event/* {\n\
        reverse_proxy 127.0.0.1:8000\n\
    }\n\
    handle /ping {\n\
        reverse_proxy 127.0.0.1:8000\n\
    }\n\
    \n\
    # Regla para la Web (SPA) - Si no encuentra el archivo, muestra index.html\n\
    try_files {path} {path}/ /index.html\n\
}" > Caddyfile

# 11. Arranque
CMD ["sh", "-c", "reflex run --env prod --backend-only --backend-port 8000 & caddy run --config Caddyfile --adapter caddyfile"]