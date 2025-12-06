FROM python:3.11
ENV CACHE_BUST=20251206_1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
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
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH
WORKDIR $HOME/app

RUN curl -fsSL https://bun.sh/install | bash
ENV PATH="/home/user/.bun/bin:$PATH"
COPY --chown=user requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
COPY --chown=user . .
USER root
RUN chmod +x start.sh
USER user
RUN reflex export --frontend-only --no-zip
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
CMD ["bash", "./start.sh"]
