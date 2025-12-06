#!/bin/bash

# 1. Diagnóstico: Mostrar si existen los archivos web
echo "--- VERIFICANDO ARCHIVOS WEB ---"
if [ -d ".web/_static" ]; then
    echo "✅ La carpeta .web/_static EXISTE."
    ls -F .web/_static
else
    echo "❌ ERROR CRÍTICO: La carpeta .web/_static NO EXISTE."
fi
echo "--------------------------------"

# 2. Iniciar Backend (Python) en segundo plano
reflex run --env prod --backend-only --backend-port 8000 &

# 3. Esperar a que Python despierte
sleep 3

# 4. Iniciar Frontend (Caddy)
caddy run --config Caddyfile --adapter caddyfile