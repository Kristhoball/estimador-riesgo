# Desactiva temporalmente la política de ejecución de scripts en tu sesión actual de PowerShell:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
# 1) Crear entorno virtual:
# python3 -m venv venv
# venv se llama el entorno virtual
# 2) Activar entorno virtual:
# .\venv\Scripts\Activate.ps1
# 3) Desactivar entorno virtual:
# deactivate
# Remover entorno virtual actual:
# Remove-Item -Recurse -Force .\venv

# pip install reflex
# Se crea el Entorno virtual para aislar las dependencias de las librerias, etc.

# Actualizar node.js

# Genera el proyecto:
# reflex init
# 0
# 1

# .web es carpeta oculta
# assets tiene tanto imagenes, fuentes, audio

# Ejecuta la pagina web:
# reflex run
# Parar el proyecto:
# ctr + c
# Al parar el proyecto, ya no se puede acceder a la pagina web

# Exporta la pagina web como app en ejecutable .zip:
# reflex export

# reflex usa librerias como Chakra UI y Tailwindcss
# En vsc ctr + p:
# >simple browser show http://localhost:3000/