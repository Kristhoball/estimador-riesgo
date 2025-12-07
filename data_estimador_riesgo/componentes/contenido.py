import reflex as rx
import tempfile
import os
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64
import zipfile
import gc
import shutil
from datetime import datetime
import time

# --- CORRECCIÓN DE IMPORTS ROBUSTA ---
try:
    from data_estimador_riesgo.codigo import Filtrar_Archivo_En_Disco
    from data_estimador_riesgo.componentes.codigo2 import Calcular_Resultados_Finales
except ImportError:
    # Fallback por si la estructura local es diferente
    try:
        from ..codigo import Filtrar_Archivo_En_Disco
        from .codigo2 import Calcular_Resultados_Finales
    except:
        from .codigo import Filtrar_Archivo_En_Disco
        from .codigo2 import Calcular_Resultados_Finales

# =========================================================================
# CACHE GLOBAL
# =========================================================================
USUARIOS_CACHE = {}
TIEMPO_EXPIRACION_MINUTOS = 30

# Carpeta segura para uploads
CARPETA_SISTEMA_TEMP = tempfile.gettempdir()
CARPETA_DATOS = os.path.join(CARPETA_SISTEMA_TEMP, "datos_usuarios_riesgo")

if not os.path.exists(CARPETA_DATOS):
    try:
        os.makedirs(CARPETA_DATOS)
    except Exception as e:
        print(f"Error creando carpeta temporal: {e}")

class State(rx.State):
    usuario_cookie: str = rx.Cookie("")

    # --- VARIABLES ---
    archivos_visuales: list[str] = []
    df_rutas: list[str] = []
    seleccionado: str = ""
    logs: list[str] = ["Sistema listo. Carga: 1.Titulados, 2.Motivación, 3.Preparación."]

    es_simulado: str = "No"

    # Variable para el input de combinatoria
    max_filas_combinatoria: str = "2000"

    procesando: bool = False
    progreso: int = 0
    historial: list[dict] = []
    tipo_simulacion: str = "Muestra estratificada por criterio de Neyman"
    vista_actual: str = "inicio"

    img_carrera: str = ""
    img_estudiantes: str = ""
    procesando_graficos: bool = False
    show_login: bool = False
    show_perfil: bool = False
    correo_input: str = ""
    pass_input: str = ""
    error_login: str = ""
    usuario_actual: str = "Usuario"
    esta_logueado: bool = False
    ver_password: bool = False

    # --- VAR CALCULADA ---
    @rx.var
    def info_estimacion_filas(self) -> str:
        try:
            val = int(self.max_filas_combinatoria)
            return f"Simulará un máximo de {val * 6} filas en total (aprox)."
        except:
            return "Ingrese un número válido."

    # --- SETTERS ---
    def set_max_filas_combinatoria(self, v):
        if v == "" or v is None:
            self.max_filas_combinatoria = ""
            return
        if v.isdigit():
            self.max_filas_combinatoria = v

    def set_correo_input(self, v): self.correo_input = v
    def set_pass_input(self, v): self.pass_input = v
    def set_tipo_simulacion(self, v): self.tipo_simulacion = v

    def set_es_simulado(self, v):
        self.es_simulado = v
        print(f"DEBUG: Modo simulado cambiado a {self.es_simulado}")

    def set_show_login(self, v): self.show_login = v
    def set_show_perfil(self, v): self.show_perfil = v
    def toggle_ver_password(self): self.ver_password = not self.ver_password

    # --- NAVEGACIÓN Y SESIÓN ---
    def ir_a_inicio(self): self.vista_actual = "inicio"
    def ir_a_upload(self): self.vista_actual = "upload"
    def ir_a_resultados(self): self.vista_actual = "resultados"
    def ir_a_historial(self): self.vista_actual = "historial"
    def mostrar_panel(self): self.vista_actual = "inicio"
    def mostrar_historial(self): self.vista_actual = "historial"

    def check_session(self):
        self.limpiar_cache_inactivos()
        if self.usuario_cookie and self.usuario_cookie in USUARIOS_CACHE:
            user_data = USUARIOS_CACHE[self.usuario_cookie]
            self.usuario_actual = self.usuario_cookie
            self.correo_input = self.usuario_cookie
            self.pass_input = user_data["pass"]
            self.historial = user_data.get("historial", [])
            self.archivos_visuales = user_data.get("archivos_visuales", [])
            self.df_rutas = user_data.get("df_rutas", [])
            self.logs = user_data.get("logs", ["Sistema listo..."])
            self.img_carrera = user_data.get("img_carrera", "")
            self.img_estudiantes = user_data.get("img_estudiantes", "")
            self.seleccionado = user_data.get("seleccionado", "")
            self.esta_logueado = True
            USUARIOS_CACHE[self.usuario_cookie]["last_active"] = time.time()
        else:
            self.esta_logueado = False

    def guardar_estado_usuario(self):
        if self.esta_logueado and self.usuario_actual:
            USUARIOS_CACHE[self.usuario_actual] = {
                "pass": self.pass_input,
                "historial": self.historial,
                "archivos_visuales": self.archivos_visuales,
                "df_rutas": self.df_rutas,
                "logs": self.logs,
                "img_carrera": self.img_carrera,
                "img_estudiantes": self.img_estudiantes,
                "seleccionado": self.seleccionado,
                "last_active": time.time()
            }

    def limpiar_cache_inactivos(self):
        ahora = time.time()
        limite = TIEMPO_EXPIRACION_MINUTOS * 60
        borrar = [k for k, v in USUARIOS_CACHE.items() if (ahora - v["last_active"]) > limite]
        for k in borrar:
            if "df_rutas" in USUARIOS_CACHE[k]:
                for ruta in USUARIOS_CACHE[k]["df_rutas"]:
                    try: os.remove(ruta)
                    except: pass
            del USUARIOS_CACHE[k]

    def intentar_login(self):
        if not self.correo_input or not self.pass_input:
            self.error_login = "Error: Faltan datos."
            return
        email = self.correo_input.strip()
        if email in USUARIOS_CACHE:
            if USUARIOS_CACHE[email]["pass"] != self.pass_input:
                self.error_login = "Contraseña incorrecta."
                return
            datos = USUARIOS_CACHE[email]
            self.historial = datos.get("historial", [])
            self.archivos_visuales = datos.get("archivos_visuales", [])
            self.df_rutas = datos.get("df_rutas", [])
            self.logs = datos.get("logs", ["Sesión restaurada."])
            self.img_carrera = datos.get("img_carrera", "")
            self.img_estudiantes = datos.get("img_estudiantes", "")
            self.seleccionado = datos.get("seleccionado", "")
        else:
            USUARIOS_CACHE[email] = {"pass": self.pass_input, "last_active": time.time()}
            self.historial = []
            self.archivos_visuales = []
            self.df_rutas = []
            self.logs = ["Bienvenido. Sistema listo."]
            self.img_carrera = ""
            self.img_estudiantes = ""
            self.seleccionado = ""

        self.usuario_actual = email; self.usuario_cookie = email
        self.esta_logueado = True; self.show_login = False; self.error_login = ""
        return rx.toast.success(f"Bienvenido, {email}")

    def cerrar_sesion(self):
        self.guardar_estado_usuario()
        self.usuario_cookie = ""; self.usuario_actual = ""; self.esta_logueado = False; self.vista_actual = "inicio"
        self.historial, self.archivos_visuales, self.df_rutas, self.logs = [], [], [], []
        self.img_carrera, self.img_estudiantes, self.seleccionado = "", "", ""

    def eliminar_cuenta(self):
        if self.usuario_actual in USUARIOS_CACHE:
            rutas = USUARIOS_CACHE[self.usuario_actual].get("df_rutas", [])
            for r in rutas:
                try: os.remove(r)
                except: pass
            del USUARIOS_CACHE[self.usuario_actual]
        self.cerrar_sesion()
        return rx.toast.success("Cuenta eliminada.")

    # --- GESTIÓN ARCHIVOS ---
    @rx.var
    def solo_archivo_titulados(self) -> list[str]:
        if len(self.archivos_visuales) > 0: return [self.archivos_visuales[0]]
        return []

    def seleccionar_archivo(self, nombre: str): self.seleccionado = nombre

    def eliminar_archivo(self, nombre: str):
        if nombre in self.archivos_visuales:
            idx = self.archivos_visuales.index(nombre)
            self.archivos_visuales.pop(idx)
            if idx < len(self.df_rutas):
                try: os.remove(self.df_rutas[idx])
                except: pass
                self.df_rutas.pop(idx)
            self.logs.append(f"Eliminado: {nombre}")
            self.guardar_estado_usuario()

    def eliminar_registro_historial(self, index: int):
        if 0 <= index < len(self.historial):
            self.historial.pop(index)
            self.guardar_estado_usuario()

    def descargar_simulacion(self, index: int):
        if 0 <= index < len(self.historial):
            registro = self.historial[index]
            mem_zip = io.BytesIO()
            with zipfile.ZipFile(mem_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
                if registro.get("img_carrera_b64"):
                    try: zf.writestr(f"grafica_carrera.png", base64.b64decode(registro["img_carrera_b64"].split(",")[1]))
                    except: pass
                if registro.get("img_estudiantes_b64"):
                    try: zf.writestr(f"grafica_estudiantes.png", base64.b64decode(registro["img_estudiantes_b64"].split(",")[1]))
                    except: pass
            mem_zip.seek(0)
            return rx.download(data=mem_zip.read(), filename=f"simulacion_{registro['hora'].replace(':','')}.zip")

    def mover_arriba(self, nombre: str):
        if nombre not in self.archivos_visuales: return
        idx = self.archivos_visuales.index(nombre)
        if idx > 0:
            self.archivos_visuales[idx], self.archivos_visuales[idx-1] = self.archivos_visuales[idx-1], self.archivos_visuales[idx]
            if idx < len(self.df_rutas) and (idx-1) < len(self.df_rutas):
                self.df_rutas[idx], self.df_rutas[idx-1] = self.df_rutas[idx-1], self.df_rutas[idx]
            self.logs.append(f"Orden: {nombre} subió.")
            self.guardar_estado_usuario()

    def mover_abajo(self, nombre: str):
        if nombre not in self.archivos_visuales: return
        idx = self.archivos_visuales.index(nombre)
        if idx < len(self.archivos_visuales) - 1:
            self.archivos_visuales[idx], self.archivos_visuales[idx+1] = self.archivos_visuales[idx+1], self.archivos_visuales[idx]
            if idx < len(self.df_rutas) and (idx+1) < len(self.df_rutas):
                self.df_rutas[idx], self.df_rutas[idx+1] = self.df_rutas[idx+1], self.df_rutas[idx]
            self.logs.append(f"Orden: {nombre} bajó.")
            self.guardar_estado_usuario()

    # --- UPLOAD ---
    async def handle_upload(self, files: list[rx.UploadFile]):
        self.procesando = True
        self.progreso = 5
        self.logs.append(f"--- Iniciando carga (Simulado: {self.es_simulado}) ---")
        yield

        num_files = len(files)
        inc = 90 // max(1, num_files)
        curr = 5

        for i, file in enumerate(files):
            nombre = file.filename
            if nombre not in self.archivos_visuales: self.archivos_visuales.append(nombre)

            tmp_in = os.path.join(CARPETA_DATOS, f"temp_in_{int(time.time())}_{i}.csv")
            tmp_out = os.path.join(CARPETA_DATOS, f"temp_out_{int(time.time())}_{i}.csv")

            try:
                self.logs.append(f"Recibiendo: {nombre}...")
                yield

                with open(tmp_in, "wb") as buffer:
                    while True:
                        chunk = await file.read(1024*1024)
                        if not chunk: break
                        buffer.write(chunk)
                gc.collect()

                self.logs.append(f"Filtrando: {nombre}...")
                yield

                filas = Filtrar_Archivo_En_Disco(tmp_in, tmp_out, es_simulado=self.es_simulado)

                if filas > 0:
                    final_path = os.path.join(CARPETA_DATOS, f"{self.usuario_actual}_{int(time.time())}_{i}.csv")
                    shutil.move(tmp_out, final_path)

                    if len(self.df_rutas) < len(self.archivos_visuales):
                        self.df_rutas.append(final_path)
                    else:
                        idx = self.archivos_visuales.index(nombre)
                        self.df_rutas[idx] = final_path
                    self.logs.append(f"-> OK ({filas} filas).")
                else:
                    self.logs.append(f"Advertencia: '{nombre}' vacío o sin carreras válidas.")

            except Exception as e:
                self.logs.append(f"Error: {str(e)}")
                if nombre in self.archivos_visuales: self.eliminar_archivo(nombre)
                yield rx.toast.error(f"Error: {str(e)}", duration=5000)

            finally:
                if os.path.exists(tmp_in):
                    try: os.remove(tmp_in)
                    except: pass
                if os.path.exists(tmp_out):
                     try: os.remove(tmp_out)
                     except: pass
                gc.collect()

            curr += inc
            self.progreso = min(curr, 99)
            yield

        self.guardar_estado_usuario()
        self.progreso = 100
        self.procesando = False
        self.logs.append("--- Carga finalizada ---")
        yield rx.toast.success("Carga lista.")

    # --- GRAFICAR ---
    async def generar_graficos(self):
        if len(self.df_rutas) < 3:
            yield rx.window_alert(f"Faltan archivos (tienes {len(self.df_rutas)} de 3).")
            return

        self.procesando_graficos = True
        yield
        import asyncio
        await asyncio.sleep(0.1)

        try:
            df_tit = pd.read_csv(self.df_rutas[0])
            df_mot = pd.read_csv(self.df_rutas[1])
            df_prep = pd.read_csv(self.df_rutas[2])

            if 'Carrera que estudias actualmente' in df_mot.columns:
                df_mot.rename(columns={'Carrera que estudias actualmente': 'nomb_carrera'}, inplace=True)
            if 'Código Carrera Nacional' in df_prep.columns:
                df_prep.rename(columns={'Código Carrera Nacional': 'nomb_carrera'}, inplace=True)

            fig1, fig2 = Calcular_Resultados_Finales(
                df_tit, df_mot, df_prep,
                tipo_simulacion=self.tipo_simulacion,
                max_filas_simuladas=self.max_filas_combinatoria
            )

            buf = io.BytesIO(); fig1.savefig(buf, format='png', bbox_inches='tight'); buf.seek(0)
            b64_carrera_raw = base64.b64encode(buf.read()).decode('utf-8')
            self.img_carrera = f"data:image/png;base64,{b64_carrera_raw}"
            plt.close(fig1)

            if fig2:
                buf = io.BytesIO(); fig2.savefig(buf, format='png', bbox_inches='tight'); buf.seek(0)
                b64_estudiantes_raw = base64.b64encode(buf.read()).decode('utf-8')
                self.img_estudiantes = f"data:image/png;base64,{b64_estudiantes_raw}"
                plt.close(fig2)
            else: self.img_estudiantes = ""

            hora = datetime.now().strftime("%H:%M:%S")
            self.historial.insert(0, {
                "hora": hora, "tipo": self.tipo_simulacion,
                "detalle": f"Simulación completada con: {self.seleccionado}",
                "archivo_origen": self.seleccionado,
                "img_carrera_b64": self.img_carrera,
                "img_estudiantes_b64": self.img_estudiantes
            })
            self.guardar_estado_usuario()

        except Exception as e:
            self.procesando_graficos = False
            yield rx.window_alert(f"Error cálculo: {str(e)}")
            return

        self.procesando_graficos = False

# ==========================================
# INTERFAZ VISUAL (MODERNIZADA Y MINIMALISTA)
# ==========================================

# Estilos base
style_card_modern = {
    "bg": "white",
    "padding": "2em",
    "border_radius": "xl",
    "box_shadow": "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)",
    "width": "100%",
    "border": "1px solid #f0f0f0",
    "transition": "all 0.2s ease-in-out",
    "_hover": {"box_shadow": "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)"}
}

style_input_box = {
    "border": "2px dashed #e2e8f0",
    "padding": "2em",
    "border_radius": "lg",
    "background_color": "gray.50",
    "cursor": "pointer",
    "_hover": {"border_color": "teal.400", "bg": "teal.50"}
}

def row_archivo_simple(nombre_archivo: str, index: int):
    return rx.hstack(
        rx.badge(f"{index + 1}", color_scheme="gray", variant="solid", border_radius="full"),
        rx.text(nombre_archivo, font_weight=rx.cond(State.seleccionado == nombre_archivo, "bold", "normal"), color=rx.cond(State.seleccionado == nombre_archivo, "teal.600", "gray.700"), font_size="0.9em", is_truncated=True),
        rx.spacer(),
        rx.hstack(
            rx.icon_button(rx.icon("arrow-up"), on_click=lambda: State.mover_arriba(nombre_archivo), size="1", variant="ghost"),
            rx.icon_button(rx.icon("arrow-down"), on_click=lambda: State.mover_abajo(nombre_archivo), size="1", variant="ghost"),
            rx.icon_button(rx.icon("trash-2"), on_click=lambda: State.eliminar_archivo(nombre_archivo), color_scheme="red", size="1", variant="ghost"),
            spacing="1"
        ),
        width="100%", padding="0.5em", border_bottom="1px solid #f0f0f0", align_items="center",
        _hover={"bg": "gray.50"}
    )

def row_log(mensaje: str):
    return rx.text(mensaje, font_family="monospace", font_size="0.85em", color="green.300")

def login_modal():
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Acceso Docente"),
            rx.dialog.description("Ingrese sus credenciales."),
            rx.vstack(
                rx.text("Usuario / Correo", font_size="0.8em", font_weight="bold"),
                rx.input(placeholder="Ej: docente@udec.cl", value=State.correo_input, on_change=State.set_correo_input),
                rx.text("Contraseña", font_size="0.8em", font_weight="bold", margin_top="0.5em"),
                rx.box(
                    rx.input(placeholder="••••••••", type=rx.cond(State.ver_password, "text", "password"), value=State.pass_input, on_change=State.set_pass_input, padding_right="2.5em"),
                    rx.icon(tag=rx.cond(State.ver_password, "eye-off", "eye"), on_click=State.toggle_ver_password, cursor="pointer", position="absolute", right="10px", top="50%", transform="translateY(-50%)", color="gray", z_index="10"),
                    position="relative", width="100%"
                ),
                rx.cond(State.error_login != "", rx.text(State.error_login, color="red", font_size="0.8em", font_weight="bold")),
                rx.hstack(
                    rx.dialog.close(rx.button("Cancelar", variant="ghost", color_scheme="gray")),
                    rx.button("Entrar", on_click=State.intentar_login, color_scheme="teal"),
                    justify_content="end", width="100%", margin_top="1.5em"
                ),
                align_items="start", spacing="2"
            ),
        ),
        open=State.show_login, on_open_change=State.set_show_login,
    )

def perfil_modal():
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Perfil de Usuario"),
            rx.dialog.description("Datos de la sesión activa."),
            rx.vstack(
                rx.text("Usuario / Correo", font_size="0.8em", font_weight="bold"),
                rx.input(value=State.usuario_actual, read_only=True, bg="gray.50"),
                rx.text("Contraseña", font_size="0.8em", font_weight="bold", margin_top="0.5em"),
                rx.box(
                    rx.input(type=rx.cond(State.ver_password, "text", "password"), value=State.pass_input, read_only=True, bg="gray.50", padding_right="2.5em"),
                    rx.icon(tag=rx.cond(State.ver_password, "eye-off", "eye"), on_click=State.toggle_ver_password, cursor="pointer", position="absolute", right="10px", top="50%", transform="translateY(-50%)", color="gray", z_index="10"),
                    position="relative", width="100%"
                ),
                rx.divider(margin_y="1em"),
                rx.alert_dialog.root(
                    rx.alert_dialog.trigger(rx.button("Eliminar Cuenta", color_scheme="red", width="100%")),
                    rx.alert_dialog.content(
                        rx.alert_dialog.title("¿Eliminar cuenta?"),
                        rx.alert_dialog.description("Esta acción borrará todos tus datos. No se puede deshacer."),
                        rx.flex(
                            rx.alert_dialog.cancel(rx.button("Cancelar", variant="soft", color_scheme="gray")),
                            rx.alert_dialog.action(rx.button("Sí, eliminar", color_scheme="red", on_click=State.eliminar_cuenta)),
                            spacing="3", margin_top="16px", justify="end",
                        ),
                    ),
                ),
                rx.hstack(rx.dialog.close(rx.button("Cerrar", color_scheme="blue")), justify_content="end", width="100%", margin_top="1em"),
                align_items="start", spacing="2"
            ),
        ),
        open=State.show_perfil, on_open_change=State.set_show_perfil,
    )

def content_inicio():
    return rx.vstack(
        # --- HEADER ---
        rx.hstack(
            rx.image(src="/logo.jpeg", width="80px", height="auto", border_radius="lg", object_fit="contain"),
            rx.heading("Modelo de Estimador de Riesgo", size="8", font_family="serif", color="gray.800"),
            align_items="center", spacing="5", margin_bottom="2em", width="100%", justify_content="start"
        ),
        
        # --- RESUMEN ---
        rx.box(
            rx.text(
                "Herramienta de analítica predictiva diseñada para detectar estudiantes en riesgo de deserción o retraso académico. "
                "Compara el desempeño histórico (data de titulados) con indicadores actuales de motivación, reprobación y preparación inicial (PAES).",
                margin_bottom="1em", color="gray.600"
            ),
            rx.text(
                "(Resumen): El sistema calcula un Índice de Riesgo Total (Ri) fusionando datos cuantitativos (tiempo de titulación) y cualitativos (motivación). "
                "Permite al cuerpo docente visualizar alertas tempranas por carrera y por estudiante.",
                color="teal.600", font_weight="bold"
            ),
            style=style_card_modern, margin_y="2em"
        ),

        # --- ÍNDICE ---
        rx.vstack(
            rx.heading("Contenidos", size="5", color="gray.800", margin_bottom="0.5em"),
            rx.hstack(
                rx.link(rx.button("Explicación del Modelo", variant="soft", color_scheme="teal"), href="#explicacion"),
                rx.link(rx.button("Instrucciones Docente", variant="soft", color_scheme="blue"), href="#docente"),
                rx.link(rx.button("Contacto", variant="soft", color_scheme="gray"), href="#contacto"),
                spacing="4"
            ),
            width="100%", margin_bottom="4em"
        ),
        
        rx.divider(border_color="gray.200", margin_y="2em"),
        
        # --- EXPLICACIÓN ---
        rx.vstack(
            rx.heading("Explicación del Modelo", size="7", font_family="serif", margin_top="1em", color="gray.800"),
            rx.box(
                rx.text(
                    "El modelo matemático se basa en la fórmula: Ri = α(APi – Bi) + β(P̄i + IPAi). "
                    "Donde (Bi) es la Brecha Histórica calculada con datos ingresados. "
                    "Si un estudiante supera esta brecha y tiene baja motivación y baja preparación inicial, se activa la Alerta Roja.",
                    color="gray.700", line_height="1.6"
                ),
                style=style_card_modern,
            ),
            id="explicacion", width="100%", align_items="start", margin_bottom="4em"
        ),
        
        rx.divider(border_color="gray.200", margin_y="2em"),
        
        # --- DOCENTE (REDDISEÑADO) ---
        rx.vstack(
            rx.heading("Docente - Instrucciones de Uso", size="7", font_family="serif", margin_top="1em", color="gray.800"),
            rx.hstack(
                rx.box(
                    rx.list.unordered(
                        rx.list.item(rx.text("Paso 1: ", font_weight="bold", color="teal.600"), "Inicie sesión con sus credenciales.", color="gray.700"),
                        rx.list.item(rx.text("Paso 2: ", font_weight="bold", color="teal.600"), "Lea la información en la pestaña 'Inicio'.", color="gray.700"),
                        rx.list.item(rx.text("Paso 3: ", font_weight="bold", color="teal.600"), "Vaya a la pestaña 'Upload'.", color="gray.700"),
                        rx.list.item(rx.text("Paso 4: ", font_weight="bold", color="teal.600"), "Cargue los archivos CSV en el orden: 1.Titulados, 2.Motivación, 3.Preparación.", color="gray.700"),
                        rx.list.item(rx.text("Paso 5: ", font_weight="bold", color="teal.600"), "Vaya a la pestaña 'Resultados'.", color="gray.700"),
                        rx.list.item(rx.text("Paso 6: ", font_weight="bold", color="teal.600"), "Seleccione el tipo de simulación y genere las alertas.", color="gray.700"),
                        spacing="4"
                    ),
                    style=style_card_modern,
                    width="60%",
                    height="auto"
                ),
                
                # VIDEO CUADRADO Y LIMPIO
                rx.vstack(
                    rx.text("Video Tutorial:", font_weight="bold", font_size="1em", color="teal.800"),
                    rx.aspect_ratio(
                        rx.video(
                            src="https://www.youtube.com/embed/8d-bT6qGqGk",
                            width="100%", height="100%", controls=True
                        ),
                        ratio=4/3,
                        width="100%",
                        border_radius="lg",
                        overflow="hidden",
                        box_shadow="lg"
                    ),
                    rx.text("(Demostración Rápida)", font_size="0.8em", color="gray.500"),
                    width="35%", align_items="center"
                ),
                width="100%", spacing="6", align_items="start"
            ),
            id="docente", width="100%", margin_bottom="4em"
        ),
        
        rx.divider(border_color="gray.200", margin_y="2em"),
        
        # --- CONTACTO ---
        rx.vstack(
            rx.heading("Contacto y Soporte", size="7", font_family="serif", margin_top="1em", color="gray.800"),
            rx.box(
                rx.vstack(
                    rx.text("Para dudas técnicas o reporte de errores, contactar al equipo de desarrollo.", color="gray.600"),
                    rx.divider(margin_y="1em"),
                    rx.link(
                        rx.hstack(rx.icon("github"), rx.text("Ver Repositorio en GitHub")),
                        href="https://github.com/Kristhoball/estimador-riesgo",
                        color="white", bg="black", padding="0.8em", border_radius="md", _hover={"opacity": 0.8}, is_external=True
                    ),
                    align_items="center"
                ),
                style=style_card_modern,
            ),
            id="contacto", width="100%", margin_bottom="4em"
        ),
        align_items="start", width="100%", padding="3em", bg="gray.50"
    )

def content_upload():
    return rx.vstack(
        rx.heading("Carga de Datos", size="8", font_family="serif", margin_bottom="0.5em", color="gray.800"),
        rx.text("Sube los archivos CSV necesarios para iniciar el análisis.", color="gray.500", margin_bottom="2em"),
        
        rx.hstack(
            # --- CAJA IZQUIERDA: INPUTS ---
            rx.box(
                rx.heading("1. Configuración", size="4", color="teal.700", margin_bottom="1em"),
                rx.vstack(
                    rx.text("¿Es una simulación?", font_weight="bold", color="gray.700"),
                    rx.hstack(
                        rx.radio_group(["Si", "No"], direction="row", on_change=State.set_es_simulado, value=State.es_simulado, color_scheme="teal"),
                        # CORRECCIÓN DE VARIANT: Usamos 'soft' o 'solid' en lugar de 'subtle'
                        rx.badge(f"Seleccionado: {State.es_simulado}", color_scheme="blue", variant="soft"),
                        align_items="center", spacing="4"
                    ),
                    width="100%", margin_bottom="2em"
                ),
                
                rx.heading("2. Archivos", size="4", color="teal.700", margin_bottom="1em"),
                rx.upload(
                    rx.vstack(
                        rx.icon("upload-cloud", size=40, color="gray"),
                        rx.text("Arrastra archivos CSV aquí", font_weight="bold", color="gray.700"),
                        rx.text("o haz clic para seleccionar", font_size="0.8em", color="gray.500"),
                        align_items="center", spacing="2"
                    ),
                    id="upload_box",
                    style=style_input_box,
                    accept={"text/csv": [".csv"]}, multiple=True
                ),
                
                rx.vstack(
                    rx.text("Archivos en cola:", font_weight="bold", color="gray.700", margin_top="1.5em"),
                    rx.scroll_area(
                        rx.vstack(
                            rx.cond(
                                State.archivos_visuales,
                                rx.foreach(State.archivos_visuales, lambda x, i: row_archivo_simple(x, i)),
                                rx.center(rx.text("Ningún archivo seleccionado", color="gray.400", padding="1em"))
                            ),
                            width="100%"
                        ),
                        height="150px", type="always", scrollbars="vertical", bg="white", border="1px solid #e2e8f0", border_radius="md"
                    ),
                    width="100%"
                ),

                rx.button(
                    "Procesar Datos", 
                    on_click=State.handle_upload(rx.upload_files(upload_id="upload_box")), 
                    loading=State.procesando, 
                    width="100%", size="3", color_scheme="teal", margin_top="2em",
                    _hover={"transform": "scale(1.02)"}
                ),
                rx.cond(
                    State.procesando, 
                    rx.box(
                        rx.text(f"Procesando... {State.progreso}%", font_size="0.8em", color="teal.600", margin_bottom="0.5em", margin_top="1em"), 
                        rx.progress(value=State.progreso, max=100, color_scheme="teal", width="100%"),
                        width="100%"
                    )
                ),
                
                style=style_card_modern,
                flex="1"
            ),
            
            # --- CAJA DERECHA: INFO Y LOGS ---
            rx.box(
                rx.heading("Estado del Sistema", size="4", color="teal.700", margin_bottom="1em"),
                
                rx.alert(
                    rx.alert_icon(),
                    rx.box(
                        rx.alert_title("Orden Requerido"),
                        rx.alert_description(
                            rx.text("1. Titulados.csv"),
                            rx.text("2. Motivacion.csv"),
                            rx.text("3. Preparacion.csv"),
                        ),
                    ),
                    status="info", variant="subtle", color_scheme="blue", margin_bottom="2em", border_radius="md"
                ),
                
                rx.text("Terminal de Procesos:", font_weight="bold", color="gray.700", margin_bottom="0.5em"),
                rx.box(
                    rx.scroll_area(
                        rx.vstack(rx.foreach(State.logs, row_log), width="100%", spacing="1", align_items="start"),
                        height="400px", type="always", scrollbars="vertical"
                    ),
                    bg="gray.900", color="green.300", font_family="monospace", padding="1em", border_radius="md", width="100%"
                ),
                
                style=style_card_modern,
                flex="1"
            ),
            width="100%", spacing="6", align_items="start"
        ),
        align_items="start", width="100%", padding="3em", bg="gray.50"
    )

def content_resultados():
    return rx.vstack(
        rx.heading("Resultados del Análisis", size="8", font_family="serif", margin_bottom="1em", color="gray.800"),
        
        # --- PANEL DE CONTROL ---
        rx.box(
            rx.hstack(
                # Selección de Archivo
                rx.vstack(
                    rx.heading("1. Fuente de Datos", size="3", color="teal.700"),
                    rx.scroll_area(
                        rx.radio_group(
                            items=State.solo_archivo_titulados, 
                            direction="column", 
                            on_change=State.seleccionar_archivo, 
                            value=State.seleccionado,
                            color_scheme="teal"
                        ), 
                        height="80px", width="100%"
                    ),
                    width="40%", align_items="start", padding_right="2em", border_right="1px solid #e2e8f0"
                ),
                
                # Selección de Algoritmo
                rx.vstack(
                    rx.heading("2. Algoritmo", size="3", color="teal.700"),
                    rx.radio_group(
                        ["Muestra estratificada por criterio de Neyman", "Combinatoria", "Eliminación"], 
                        direction="column", 
                        on_change=State.set_tipo_simulacion, 
                        value=State.tipo_simulacion,
                        color_scheme="blue"
                    ),
                    # Input condicional bonito
                    rx.cond(
                        State.tipo_simulacion == "Combinatoria",
                        rx.box(
                            rx.text("Filas máx. por carrera:", font_size="0.8em", color="gray.500", margin_top="0.5em"),
                            rx.input(
                                value=State.max_filas_combinatoria,
                                on_change=State.set_max_filas_combinatoria,
                                type="number", placeholder="Ej: 2000", max_length=5,
                                border_color="teal.200", focus_border_color="teal.500"
                            ),
                            rx.text(State.info_estimacion_filas, font_size="0.7em", color="orange.500", margin_top="0.2em"),
                            margin_top="0.5em", width="100%"
                        )
                    ),
                    width="40%", align_items="start"
                ),
                
                # Botón de Acción
                rx.center(
                    rx.button(
                        "Generar Alertas", 
                        on_click=State.generar_graficos, 
                        loading=State.procesando_graficos, 
                        size="4", 
                        color_scheme="teal",
                        width="100%",
                        _hover={"transform": "scale(1.05)"}
                    ),
                    width="20%"
                ),
                
                width="100%", spacing="4", align_items="start"
            ),
            style=style_card_modern, margin_bottom="2em"
        ),
        
        # --- GRÁFICOS ---
        rx.heading("Riesgo por Carrera (Macro)", size="5", color="gray.700", margin_bottom="0.5em"),
        rx.box(
            rx.cond(
                State.img_carrera != "", 
                rx.image(src=State.img_carrera, width="100%", height="auto", border_radius="lg"), 
                rx.center(rx.vstack(rx.icon("bar-chart-2", size=40, color="gray"), rx.text("Gráfico no generado", color="gray.400")), padding="4em")
            ), 
            style=style_card_modern, margin_bottom="2em"
        ),
        
        rx.heading("Riesgo por Estudiante (Micro)", size="5", color="gray.700", margin_bottom="0.5em"),
        rx.box(
            rx.cond(
                State.img_estudiantes != "", 
                rx.image(src=State.img_estudiantes, width="100%", height="auto", border_radius="lg"), 
                rx.center(rx.vstack(rx.icon("users", size=40, color="gray"), rx.text("Gráfico no generado", color="gray.400")), padding="4em")
            ), 
            style=style_card_modern, height="600px", overflow="auto"
        ),
        
        align_items="start", width="100%", padding="3em", bg="gray.50"
    )

def content_historial():
    return rx.vstack(
        rx.heading("Historial de Simulaciones", size="8", font_family="serif", margin_bottom="1em", color="gray.800"),
        rx.vstack(
            rx.foreach(
                State.historial,
                lambda registro, index: rx.box(
                    rx.hstack(
                        rx.vstack(
                            rx.hstack(
                                # CORRECCIÓN DE VARIANT: Usamos 'solid' o 'soft' en lugar de 'subtle'
                                rx.badge(f"{registro['hora']}", color_scheme="gray", variant="solid"),
                                rx.badge(registro["tipo"], color_scheme="blue", variant="soft"),
                                spacing="2"
                            ),
                            rx.text(registro["detalle"], font_size="sm", color="gray.600", margin_top="0.5em"),
                            align_items="start", spacing="0"
                        ),
                        rx.spacer(), 
                        rx.hstack(
                            rx.tooltip(rx.icon_button(rx.icon("download"), on_click=lambda: State.descargar_simulacion(index), color_scheme="green", variant="soft", size="2"), label="Descargar ZIP"),
                            rx.tooltip(rx.icon_button(rx.icon("trash-2"), on_click=lambda: State.eliminar_registro_historial(index), color_scheme="red", variant="ghost", size="2"), label="Eliminar"),
                            spacing="2"
                        ),
                        width="100%", align_items="center"
                    ),
                    bg="white", padding="1.5em", border_radius="lg", width="100%", 
                    box_shadow="0 2px 4px rgba(0,0,0,0.05)", border="1px solid #f0f0f0",
                    _hover={"box_shadow": "0 4px 6px rgba(0,0,0,0.1)"}
                )
            ),
            width="100%", spacing="3"
        ),
        align_items="start", width="100%", padding="3em", bg="gray.50", height="100vh", overflow="auto"
    )

def contenido() -> rx.Component:
    # 1. PIEZAS
    vista_acceso_restringido = rx.center(
        rx.vstack(
            rx.icon("lock", size=60, color="gray"),
            rx.heading("Acceso Restringido", size="8", color="gray.600"),
            rx.text("Por favor inicie sesión para ver el panel completo.", color="gray.500"),
            rx.button("Iniciar Sesión", on_click=lambda: State.set_show_login(True), size="4", color_scheme="teal", margin_top="1em", variant="surface"),
            spacing="4", align_items="center"
        ), height="80vh", width="100%", bg="gray.50"
    )

    contenido_dinamico = rx.cond(
        State.vista_actual == "historial",
        content_historial(),
        rx.cond(
            State.vista_actual == "resultados",
            content_resultados(),
            rx.cond(
                State.vista_actual == "upload",
                content_upload(),
                content_inicio() 
            )
        )
    )

    # 2. BARRA SUPERIOR
    barra_superior = rx.hstack(
        rx.spacer(), 
        rx.cond(
            State.esta_logueado,
            rx.hstack(
                # CORRECCIÓN DE VARIANT
                rx.badge(f"👤 {State.usuario_actual}", color_scheme="green", variant="soft", padding="0.5em"),
                rx.button("Mi Perfil", on_click=lambda: State.set_show_perfil(True), variant="ghost", size="2", color_scheme="gray"),
                perfil_modal(), 
                rx.button("Salir", on_click=State.cerrar_sesion, color_scheme="red", variant="ghost", size="2"),
                spacing="4", align_items="center"
            ),
            rx.box(
                rx.button("Acceso Docente", on_click=lambda: State.set_show_login(True), variant="solid", color_scheme="teal"),
                login_modal()
            )
        ),
        width="100%", padding="1.2em", border_bottom="1px solid #e2e8f0", bg="white", position="sticky", top="0", z_index="50"
    )

    return rx.box(
        rx.script("console.log('App montada')"),
        barra_superior,
        rx.box(
            rx.cond(
                State.esta_logueado,
                contenido_dinamico,
                vista_acceso_restringido
            ),
            width="100%"
        ),
        on_mount=State.check_session, 
        width="100%", height="100vh", overflow="auto", background_color="gray.50"
    )
