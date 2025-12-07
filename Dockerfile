# CAMBIO 1: Usamos la imagen COMPLETA
FROM python:3.11

# 1. Configuración básica y ROMPE-CACHÉ
# Subimos a _9 para obligar a Zeabur a leer el código arreglado de barra.py
ENV CACHE_BUST=20251206_9
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

# 4. INSTALACIÓN MANUAL DE BUN 
RUN curl -fsSL https://bun.sh/install | bash
ENV PATH="/home/user/.bun/bin:$PATH"

# 5. Instalar Dependencias Python
COPY --chown=user requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# 6. COPIAR CÓDIGO (Aquí se copia tu barra.py arreglado)
COPY --chown=user . .

# 7. Asegurar permisos de ejecución
USER root
RUN chmod +x start.sh
USER user

# 8. Exportar frontend (Ahora sí debería funcionar sin errores)
RUN reflex export --frontend-only --no-zip

CMD ["bash", "./start.sh"]
