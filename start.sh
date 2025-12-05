#!/bin/bash

# Este script se asegura de que el Frontend y el Backend corran juntos.

# 1. Ejecutar el Backend (Python) en segundo plano en el puerto 8000
reflex run --env prod --backend-only --backend-port 8000 &

# 2. Esperar unos segundos para que el backend esté listo
sleep 5

# 3. Arrancar Caddy (el servidor web) en el puerto 8080 (o 7860 para Hugging Face)
# En Zeabur o Google, usamos el puerto que nos piden (generalmente 8080)
# Vamos a usar el puerto 8080.
caddy run --config Caddyfile --adapter caddyfile --listen :8080