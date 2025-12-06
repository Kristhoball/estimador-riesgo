# 1. Usamos una imagen base de Python oficial y ligera
FROM python:3.11-slim

# 2. Configuración de entorno
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Instalar Caddy y util-linux
RUN apt-get update && apt-get install -y \
    curl unzip util-linux caddy \
    && rm -rf /var/lib/apt/lists/*

# 4. Crear directorio de trabajo y usuario no-root
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH
WORKDIR $HOME/app

# 5. Copiar requisitos e instalar librerías
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# 6. Copiar el código del proyecto
COPY . .

# 7. Limpiar permisos (Para evitar errores de reflex init)
RUN rm -f .gitignore requirements.txt

# 8. Inicializar y Exportar el Frontend
RUN reflex init
RUN reflex export --frontend-only --no-zip

# 9. URL Pública (HTTPS) para Reflex
# Reemplaza esto con tu dominio real de Zeabur
ENV REFLEX_API_URL=https://estimador-riesgo.zeabur.app

# 10. Configuración de Caddy (CORREGIDA)
# El bloque { auto_https off } va PRIMERO y separado.
RUN echo "{\n\
    auto_https off\n\
}\n\
\n\
:8080 {\n\
    handle /_event/* {\n\
        reverse_proxy 127.0.0.1:8000\n\
    }\n\
    handle /ping {\n\
        reverse_proxy 127.0.0.1:8000\n\
    }\n\
    handle /* {\n\
        root * .web/_static\n\
        file_server\n\
        try_files {path} {path}/ /index.html\n\
    }\n\
}" > Caddyfile

# 11. Arranque FINAL
CMD ["sh", "-c", "reflex run --env prod --backend-only --backend-port 8000 & caddy run --config Caddyfile --adapter caddyfile"]