FROM python:3.11-slim

# 1. Configuración básica y ROMPE-CACHÉ
# Cambia este número si necesitas forzar una reconstrucción completa en el futuro
ENV CACHE_BUST=20250228_1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 2. Instalar herramientas del sistema
# Usamos --no-install-recommends para mantenerlo ligero, pero aseguramos unzip
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    unzip \
    debian-keyring \
    debian-archive-keyring \
    apt-transport-https \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 3. VERIFICACIÓN (Esto fallará la build si unzip no se instaló, avisándonos antes)
RUN which unzip && unzip -v | head -n 1

# 4. Instalar Caddy (Servidor Web)
RUN curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg \
    && curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list \
    && apt-get update && apt-get install -y caddy \
    && rm -rf /var/lib/apt/lists/*

# 5. Crear usuario (Seguridad)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH
WORKDIR $HOME/app

# 6. Instalar Dependencias Python
COPY --chown=user requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# 7. Copiar Código
COPY --chown=user . .

# 8. Asegurar permisos de ejecución
RUN chmod +x start.sh

# 9. Construir Frontend (Reflex Export)
# Ahora unzip está garantizado, así que esto no debería fallar
RUN reflex export --frontend-only --no-zip

# 10. Configurar Caddy
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

# 11. Comando de arranque
CMD ["bash", "./start.sh"]
