#!/bin/bash
    # Iniciar el backend en el puerto 8000
    python3 -m reflex run --env prod --backend-only --loglevel debug
    
    # Nota: Caddy se inicia en segundo plano o mediante el Dockerfile directamente,
    # pero este script debe mantener vivo el proceso del backend.