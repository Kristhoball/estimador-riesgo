#!/bin/bash

# 1. Iniciar Caddy (El servidor web) en segundo plano
caddy start --config Caddyfile --adapter caddyfile &

# 2. Iniciar el Backend de Reflex
python3 -m reflex run --env prod --backend-only --loglevel debug
