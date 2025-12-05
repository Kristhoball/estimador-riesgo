# 1. Usamos una imagen base de Python oficial y ligera
FROM python:3.11-slim

# 2. Configuración de entorno
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Instalar Caddy y util-linux (necesario para que reflex compile)
RUN apt-get update && apt-get install -y \
    curl unzip util-linux caddy \
    && rm -rf /var/lib/apt/lists/*

# 4. Crear directorio de trabajo y usuario no-root (Obligatorio en Zeabur/Cloud)
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

# 7. CORRECCIÓN CRÍTICA DE PERMISOS
# Eliminamos cualquier archivo .gitignore bloqueado antes de que reflex init intente crearlo
RUN rm -f .gitignore 

# 8. Inicializar y Exportar el Frontend
RUN reflex init
RUN reflex export --frontend-only --no-zip

# 9. Configuración de Caddy (Frontend en 8080)
# Esto le dice a Caddy que escuche en 8080 (Zeabur/Cloud) y mande peticiones al Python en 8000
RUN echo "0.0.0.0:8080 {\n\
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

# 10. Arranque FINAL: Ejecutar Python en segundo plano y Caddy en primer plano
CMD ["sh", "-c", "reflex run --env prod --backend-only --backend-port 8000 & caddy run --config Caddyfile --adapter caddyfile --host 0.0.0.0"]