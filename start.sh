#!/bin/bash

# Asegurar herramientas en el PATH
export PATH="/home/user/.bun/bin:$PATH"

echo "=================================================="
echo "🚑 MODO RECUPERACIÓN ACTIVADO"
echo "=================================================="

# 1. RED DE SEGURIDAD: Intentar instalar dependencias aquí
# Si el requirements.txt estaba mal antes, esto lo arreglará ahora mismo.
echo "--- 1. Verificando librerías críticas ---"
pip install -r requirements.txt

# 2. LIMPIEZA
echo -e "\n--- 2. Limpiando construcciones previas ---"
rm -rf .web

# 3. GENERACIÓN DEL FRONTEND
echo "--- 3. Generando Frontend (Con logs detallados) ---"
# Usamos -v para ver si hay errores de importación (ModuleNotFoundError)
reflex export --frontend-only --no-zip --loglevel debug

# 4. VERIFICACIÓN
echo "--- 4. Verificando resultado ---"
if [ -f ".web/_static/index.html" ]; then
    echo "✅ ÉXITO: index.html generado correctamente."
else
    echo "❌ ERROR CRÍTICO: index.html NO se generó."
    echo "Posible causa: Error en el código Python o falta una librería."
fi

echo "=================================================="
echo "🚀 Iniciando Servidores..."
echo "=================================================="

# Iniciar Caddy en segundo plano
caddy start --config Caddyfile --adapter caddyfile &

# Iniciar Backend
python3 -m reflex run --env prod --backend-only --loglevel debug
