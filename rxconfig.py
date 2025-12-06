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
    
    # 1. Quitamos el warning del sitemap
    disable_plugins=["reflex.plugins.sitemap.SitemapPlugin"],
    
    # 2. Aumentamos el tiempo de espera del backend a 20 minutos.
    # Esto ayuda a que no se corte la conexión si el archivo tarda en procesarse.
    timeout=1200,
)
