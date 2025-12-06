#!/bin/bash

export PATH="/home/user/.bun/bin:$PATH"

echo "=================================================="
echo "🛠️ ARREGLANDO RUTAS DE DESPLIEGUE"
echo "=================================================="

# 1. Instalar dependencias (por seguridad)
pip install -r requirements.txt

# 2. Limpiar todo lo anterior
rm -rf .web

# 3. Generar el Frontend
echo "--- Generando Frontend ---"
reflex export --frontend-only --no-zip --loglevel debug

# 4. BUSCAR Y MOVER (La Solución Definitiva)
echo "--- Buscando dónde quedó el index.html ---"
# Buscamos el archivo en cualquier subcarpeta de .web
FOUND_INDEX=$(find .web -name "index.html" | head -n 1)

if [ -z "$FOUND_INDEX" ]; then
    echo "❌ ERROR FATAL: No se generó index.html en NINGUNA parte."
    ls -R .web
else
    echo "✅ Encontrado en: $FOUND_INDEX"
    
    # Creamos la carpeta destino si no existe
    mkdir -p .web/_static

    # Si el archivo NO está ya en _static, movemos todo el contenido
    if [[ "$FOUND_INDEX" != *".web/_static/index.html"* ]]; then
        echo "📦 Moviendo archivos de la carpeta de construcción a _static..."
        
        # Obtenemos la carpeta donde está el index.html (ej: .web/build/client)
        SOURCE_DIR=$(dirname "$FOUND_INDEX")
        
        # Copiamos todo el contenido de esa carpeta a _static
        cp -r "$SOURCE_DIR/"* .web/_static/
        
        echo "✅ Archivos movidos correctamente."
        ls -la .web/_static/index.html
    else
        echo "✅ El archivo ya estaba en el lugar correcto."
    fi
fi

echo "=================================================="
echo "🚀 Arrancando Servidores"
echo "=================================================="

# Iniciar Caddy
caddy start --config Caddyfile --adapter caddyfile &

# Iniciar Backend
python3 -m reflex run --env prod --backend-only --loglevel debug
