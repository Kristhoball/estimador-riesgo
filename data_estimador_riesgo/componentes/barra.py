import reflex as rx
from .contenido import State

def boton_menu(nombre: str, vista_destino: str, funcion_click):
    # Lógica de estilo "activo" vs "inactivo"
    es_activo = State.vista_actual == vista_destino

    return rx.button(
        nombre, 
        on_click=funcion_click,
        variant="ghost",
        width="100%",
        justify_content="start",
        padding="1em",
        border_radius="8px",
        
        # Estilos condicionales
        bg=rx.cond(es_activo, "rgba(72, 187, 120, 1)", "transparent"),
        color=rx.cond(es_activo, "white", "black"),
        box_shadow=rx.cond(es_activo, "0 4px 6px -1px rgba(72, 187, 120, 0.4)", "none"),
        
        _hover={
            "bg": rx.cond(es_activo, "rgba(56, 161, 105, 1)", "rgba(240, 255, 244, 1)"),
            "border": rx.cond(es_activo, "1px solid transparent", "1px solid #9AE6B4"),
            "color": rx.cond(es_activo, "white", "#2F855A"),
            "transform": "translateX(5px)",
        },
        transition="all 0.2s ease-in-out",
        cursor="pointer",
        border="1px solid transparent"
    )

def barra() -> rx.Component:
    return rx.vstack(
        # --- ZONA DEL LOGO ---
        rx.box(
            rx.center(
                rx.image(
                    # ACTUALIZADO: Usa 'logo.jpeg' exacto.
                    # Asegúrate de que el archivo esté en la carpeta 'assets' con ese nombre.
                    src="/logo.jpeg", 
                    width="140px", 
                    height="auto",
                    alt="Logo Institucional",
                    object_fit="contain"
                )
            ),
            padding="1.5em", 
            width="100%", 
            border_bottom="1px solid #e0e0e0"
        ),
        
        # Navegación con Botones Bonitos
        rx.vstack(
            boton_menu("Inicio", "inicio", State.ir_a_inicio),
            boton_menu("Upload", "upload", State.ir_a_upload),
            boton_menu("Resultados", "resultados", State.ir_a_resultados),
            boton_menu("Historial", "historial", State.ir_a_historial),
            
            width="100%",
            spacing="3",
            padding_x="1em",
            margin_top="2em"
        ),
        
        rx.spacer(),
        
        # Zona Usuario (Pie de barra)
        rx.vstack(
            rx.divider(),
            rx.cond(
                State.esta_logueado,
                rx.vstack(
                    rx.button(f"👤 {State.usuario_actual}", variant="ghost", width="100%", justify_content="start", color_scheme="gray", on_click=lambda: State.set_show_perfil(True)),
                    rx.button("Cerrar Sesión", on_click=State.cerrar_sesion, variant="ghost", width="100%", justify_content="start", color="red", _hover={"bg": "#FFF5F5", "border": "1px solid #FEB2B2"}),
                    width="100%", spacing="0"
                ),
                rx.button("Iniciar Sesión", on_click=lambda: State.set_show_login(True), variant="ghost", width="100%", justify_content="start", color_scheme="teal")
            ),
            width="100%", padding="1em"
        ),
        
        height="100vh", width="250px", border_right="1px solid #e0e0e0", bg="white", flex_shrink="0", align_items="start"
    )
