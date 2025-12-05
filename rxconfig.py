import reflex as rx

config = rx.Config(
    app_name="data_estimador_riesgo",
    
    # --- CAMBIO CRÍTICO: LA URL DE ZEABUR ---
    # Esto le dice al frontend que busque el servidor en la nube, no en localhost
    api_url="https://estimador-riesgo.zeabur.app",
    
    # CORS: Permite que la nube y tu PC se conecten
    cors_allowed_origins=[
        "http://localhost:3000",
        "https://estimador-riesgo.zeabur.app"
    ],
)