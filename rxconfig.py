import reflex as rx

config = rx.Config(
    app_name="data_estimador_riesgo",
    
    # ESTA ES LA CLAVE: Decirle dónde está el backend
    # Usamos la URL pública de tu espacio en Hugging Face
    api_url="https://cristobramos4-data-estimador-riesgo.hf.space",
    
    # CORS (Permisos de seguridad)
    cors_allowed_origins=[
        "http://localhost:3000",
        "https://cristobramos4-data-estimador-riesgo.hf.space"
    ],
)