import reflex as rx

config = rx.Config(
    app_name="data_estimador_riesgo",

    # --- CONFIGURACIÓN DE ZEABUR ---
    # URL de tu proyecto en Zeabur (Debe ser HTTPS)
    api_url="https://estimador-riesgo.zeabur.app",
    
    # Permitir conexiones seguras desde el host de Zeabur
    cors_allowed_origins=[
        "http://localhost:3000",
        "https://estimador-riesgo.zeabur.app"
    ],

    # --- CORRECCIONES NUEVAS ---
    
    # 1. Elimina el Warning del Sitemap del log
    disable_plugins=["reflex.plugins.sitemap.SitemapPlugin"],

    # 2. Configuración para subir archivos grandes (130MB+)
    api=rx.ApiConfig(
        upload_max_size=500 * 1024 * 1024,  # 500 MB en bytes
    ),
    
    # 3. Timeout extendido: 20 minutos
    # Vital para que Zeabur no corte la conexión mientras sube el archivo
    timeout=1200,
)
