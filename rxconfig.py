import reflex as rx

config = rx.Config(
    app_name="data_estimador_riesgo",
    
    # URL de tu proyecto en Zeabur (Debe ser HTTPS)
    api_url="https://estimador-riesgo.zeabur.app",
    
    # Permitir conexiones seguras desde el host de Zeabur
    cors_allowed_origins=[
        "http://localhost:3000",
        "https://estimador-riesgo.zeabur.app"
    ],
)