import reflex as rx
from .componentes.barra import barra
from .componentes.contenido import contenido

# Definir el estado global de la app (estado de variable reactiva y funcion)
class  State(rx.State):
    pass


# Definir lo que se muestra en la página principal
def index() -> rx.Component:
    return rx.tabs.root(
        rx.hstack(
            # --- SIDEBAR (Izquierda) ---
            barra(),
            # --- AREA DE CONTENIDO (Derecha) ---
            contenido(),
            spacing="0",
            width="100%",
            height="100vh"
        ),
        default_value="inicio", # Tab por defecto
        orientation="vertical",
        width="100%"
    )


app = rx.App() # Crear una instancia de la app
app.add_page(index) # Registrar la función 'index' como página principal
app._compile() # Compilar la app para que Reflex genere los archivos necesarios

