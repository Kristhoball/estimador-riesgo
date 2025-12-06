# 1. Imagen base
FROM python:3.11-slim

# 2. Configuración
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Instalar Caddy y util-linux
RUN apt-get update && apt-get install -y \
    curl unzip util-linux caddy \
    && rm -rf /var/lib/apt/lists/*

# 4. Usuario seguro
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH
WORKDIR $HOME/app

# 5. Copiar archivos
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
COPY . .

# 6. Limpiar permisos
RUN rm -f .gitignore requirements.txt

# 7. Inicializar
RUN reflex init

# --- AQUÍ ESTÁ LA CLAVE DEL HTTPS ---
# Le decimos a Reflex: "Tu dirección pública es HTTPS"
ENV REFLEX_API_URL=https://estimador-riesgo.zeabur.app

# 8. Construir la Web
RUN reflex export --frontend-only --no-zip

# 9. Configuración de Caddy (CORREGIDA PARA ACEPTAR CUALQUIER DOMINIO)
# Usamos ":8080" en lugar de una IP específica. Esto permite que Zeabur entre.
RUN echo ":8080 {\n\
    # Desactivamos el auto-HTTPS de Caddy porque Zeabur ya lo hace afuera\n\
    auto_https off\n\
    \n\
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

# 10. Arranque FINAL
# Quitamos flags innecesarios, la configuración ya está en el archivo Caddyfile
CMD ["sh", "-c", "reflex run --env prod --backend-only --backend-port 8000 & caddy run --config Caddyfile --adapter caddyfile"]