FROM python:3.11-slim

# Configuración de entorno
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 1. Instalar Caddy y util-linux
RUN apt-get update && apt-get install -y \
    curl unzip util-linux caddy \
    && rm -rf /var/lib/apt/lists/*

# 2. Directorio de trabajo y usuario
WORKDIR /app
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH
WORKDIR $HOME/app

# 3. Copiar y construir
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
COPY . .

# 4. Inicializar y Exportar (El Frontend)
RUN reflex init
RUN reflex export --frontend-only --no-zip

# 5. Configuración de Caddy (Usando el puerto 8080 para el mundo)
# El puerto interno de Python sigue siendo 8000
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

# 6. Arranque FINAL
# Arranca Python en segundo plano (&) y luego arranca Caddy
CMD ["sh", "-c", "reflex run --env prod --backend-only --backend-port 8000 & caddy run --config Caddyfile --adapter caddyfile --host 0.0.0.0"]