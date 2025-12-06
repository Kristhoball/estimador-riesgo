#!/bin/bash

# Asegurar que encontramos 'bun' y otras herramientas
export PATH="/home/user/.bun/bin:$PATH"

echo "🛠️ GENERANDO FRONTEND (Esto puede tardar unos segundos)..."
# Forzamos la creación de la página web aquí mismo
reflex export --frontend-only --no-zip

echo "✅ Frontend generado. Verificando:"
ls -l .web/_static/index.html

echo "🚀 Iniciando Servidores..."

# 1. Iniciar Caddy (Servidor Web) en segundo plano
caddy start --config Caddyfile --adapter caddyfile &

# 2. Iniciar Backend Reflex
python3 -m reflex run --env prod --backend-only --loglevel debug
