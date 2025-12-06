import reflex as rx

config = rx.Config(
    app_name="data_estimador_riesgo",

    # --- CONFIGURACIÓN DE ZEABUR ---
    api_url="https://estimador-riesgo.zeabur.app",
    
    cors_allowed_origins=[
        "http://localhost:3000",
        "https://estimador-riesgo.zeabur.app"
    ],

    # --- CORRECCIONES ---
    
    # 1. Mantenemos esto para limpiar el log (es válido según tu warning anterior)
    disable_plugins=["reflex.plugins.sitemap.SitemapPlugin"],

    # 2. ELIMINADO: api=rx.ApiConfig(...) 
    # Causa el error "AttributeError: No reflex attribute ApiConfig".
    # Reflex gestionará la subida con los valores predeterminados del servidor.
)
