# CAMBIO 1: Usamos la imagen COMPLETA (no slim) para asegurar compatibilidad
FROM python:3.11

# 1. Configuración básica y ROMPE-CACHÉ
# Incrementamos esto para asegurar que Zeabur reconstruya todo
ENV CACHE_BUST=20250228_3
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 2. Instalar Caddy y herramientas del sistema
RUN apt-get update && apt-get install -y \
    curl \
    unzip \
    zip \
    debian-keyring \
    debian-archive-keyring \
    apt-transport-https \
    && curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg \
    && curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list \
    && apt-get update && apt-get install -y caddy \
    && rm -rf /var/lib/apt/lists/*

# 3. Crear usuario
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH
WORKDIR $HOME/app

# 4. INSTALACIÓN MANUAL DE BUN (La Solución Definitiva)
# Al instalar Bun manualmente, evitamos que Reflex intente hacerlo y falle buscando unzip.
RUN curl -fsSL https://bun.sh/install | bash
# Agregamos Bun al PATH para que Reflex lo encuentre
ENV PATH="/home/user/.bun/bin:$PATH"

# 5. Instalar Dependencias Python
COPY --chown=user requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# 6. Copiar Código
COPY --chown=user . .

# 7. Asegurar permisos de ejecución
USER root
RUN chmod +x start.sh
USER user

# 8. Construir Frontend (Reflex Export)
# Ahora Reflex encontrará 'bun' en el PATH y se saltará la instalación automática
RUN reflex export --frontend-only --no-zip

# 9. Configurar Caddy
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

# 10. Comando de arranque
CMD ["bash", "./start.sh"]
