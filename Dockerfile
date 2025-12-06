FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 1. Instalar dependencias del sistema y Caddy
RUN apt-get update && apt-get install -y \
    curl unzip util-linux \
    debian-keyring debian-archive-keyring apt-transport-https \
    && curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg \
    && curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list \
    && apt-get update && apt-get install -y caddy \
    && rm -rf /var/lib/apt/lists/*

# 2. Configurar Usuario (Seguridad)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH
WORKDIR $HOME/app

# 3. Instalar dependencias de Python
COPY --chown=user requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# 4. Copiar todo el código (Aquí debe venir la carpeta que falta)
COPY --chown=user . .

# 5. Limpieza y permisos
# Borramos venv si se copió por error para no confundir a Python
RUN rm -rf venv .gitignore
RUN chmod +x start.sh

# 6. Configurar URL del backend (AJUSTA ESTO SI ES NECESARIO)
ENV REFLEX_API_URL=https://estimador-riesgo.zeabur.app

# 7. Construir el Frontend (Exportar a estático)
# Al quitar 'reflex init', confiamos en que tu código ya está ahí
RUN reflex export --frontend-only --no-zip

# 8. Configurar Caddy (Servidor Web)
RUN echo "{\n\
    auto_https off\n\
}\n\
\n\
:8080 {\n\
    encode gzip\n\
    handle /_event/* {\n\
        reverse_proxy 127.0.0.1:8000\n\
    }\n\
    handle /ping {\n\
        reverse_proxy 127.0.0.1:8000\n\
    }\n\
    handle {\n\
        root * /home/user/app/.web/_static\n\
        try_files {path} {path}/ /index.html\n\
        file_server\n\
    }\n\
}" > Caddyfile

# 9. Ejecutar script de arranque
CMD ["./start.sh"]