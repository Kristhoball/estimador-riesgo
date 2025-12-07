# TRUCO 1: Usamos la versión 'slim' (ligera) de Python para ahorrar unos 200MB de RAM base
FROM python:3.11-slim

# TRUCO 2: Limitamos la memoria del constructor web (Node) a 600MB
# Esto evita que se coma toda la RAM y cause el error SIGKILL
ENV NODE_OPTIONS="--max-old-space-size=600"

# Actualizamos caché para forzar reconstrucción
ENV CACHE_BUST=20251207_LOW_RAM_v1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instalamos dependencias del sistema necesarias (al ser slim, hay que instalar más cosas manuales)
RUN apt-get update && apt-get install -y \
    curl \
    unzip \
    zip \
    git \
    debian-keyring \
    debian-archive-keyring \
    apt-transport-https \
    && curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg \
    && curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list \
    && apt-get update && apt-get install -y caddy \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH
WORKDIR $HOME/app

# Instalación de Bun
RUN curl -fsSL https://bun.sh/install | bash
ENV PATH="/home/user/.bun/bin:$PATH"

# TRUCO 3: Instalamos librerías SIN caché (--no-cache-dir) para no llenar la RAM/Disco temporalmente
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copiar Código
COPY --chown=user . .

# Permisos
USER root
RUN chmod +x start.sh
USER user

# Exportar frontend (Ahora respetará el límite de 600MB gracias al TRUCO 2)
RUN reflex export --frontend-only --no-zip

CMD ["bash", "./start.sh"]
