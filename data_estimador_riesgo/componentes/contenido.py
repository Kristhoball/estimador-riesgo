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
# INTERFAZ VISUAL
# ==========================================
style_border_box = {"border": "1px solid black", "padding": "1.5em", "border_radius": "md", "bg": "white", "width": "100%"}

def row_archivo_simple(nombre_archivo: str, index: int):
    return rx.hstack(
        rx.text(f"{index + 1}.", font_weight="bold", color="gray", font_size="0.9em"),
        rx.text(nombre_archivo, font_weight=rx.cond(State.seleccionado == nombre_archivo, "bold", "normal"), color=rx.cond(State.seleccionado == nombre_archivo, "teal", "black"), font_size="0.9em", is_truncated=True),
        rx.spacer(),
        rx.hstack(
            rx.icon(tag="arrow-up", size=14, cursor="pointer", on_click=lambda: State.mover_arriba(nombre_archivo)),
            rx.icon(tag="arrow-down", size=14, cursor="pointer", on_click=lambda: State.mover_abajo(nombre_archivo)),
            rx.icon(tag="trash-2", color="red", size=14, cursor="pointer", on_click=lambda: State.eliminar_archivo(nombre_archivo)),
            spacing="2"
        ),
        width="100%", padding="0.3em", border_bottom="1px solid #eee", align_items="center"
    )

def row_log(mensaje: str):
    return rx.text(mensaje, font_family="monospace", font_size="0.85em", color="#333")

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
        # --- HEADER CON LOGO ---
        rx.hstack(
            rx.image(
                src="/logo.jpeg", # IMPORTANTE: Ruta absoluta para el archivo en assets/logo.jpeg
                width="100px",
                height="auto",
                border_radius="10px",
                object_fit="contain"
            ),
            rx.heading("Modelo de Estimador de riesgo", size="8", font_family="serif"),
            align_items="center",
            spacing="5",
            margin_bottom="1em",
            width="100%",
            justify_content="start"
        ),

        # --- DESCRIPCIÓN GENERAL ---
        rx.box(
            rx.text(
                "Herramienta de analítica predictiva diseñada para detectar estudiantes en riesgo de deserción o retraso académico. "
                "Compara el desempeño histórico (data de titulados) con indicadores actuales de motivación, reprobación y preparación inicial (PAES).",
                margin_bottom="0.5em"
            ),
            rx.text(
                "(Resumen): El sistema calcula un Índice de Riesgo Total (Ri) fusionando datos cuantitativos (tiempo de titulación) y cualitativos (motivación). "
                "Permite al cuerpo docente visualizar alertas tempranas por carrera y por estudiante.",
                color="red",
                font_weight="bold"
            ),
            style=style_border_box,
            margin_y="2em"
        ),

        # --- ÍNDICE ---
        rx.vstack(
            rx.heading("Index :", size="5"),
            rx.scroll_area(
                rx.vstack(
                    rx.link("• Explicación", href="#explicacion", color="blue", text_decoration="underline"),
                    rx.link("• Docente", href="#docente", color="blue", text_decoration="underline"),
                    rx.link("• Contacto", href="#contacto", color="blue", text_decoration="underline"),
                    spacing="3"
                ),
                type="always", scrollbars="vertical", style={"height": "150px", "border": "1px solid black", "padding": "1em", "width": "100%"}
            ),
            width="100%", max_width="400px", align_items="start", margin_bottom="4em"
        ),

        rx.divider(border_color="black"),

        # --- EXPLICACIÓN ---
        rx.vstack(
            rx.heading("Explicación del Modelo", size="8", font_family="serif", margin_top="1em"),
            rx.box(
                rx.text(
                    "El modelo matemático se basa en la fórmula: Ri = α(APi – Bi) + β(P̄i + IPAi). "
                    "Donde (Bi) es la Brecha Histórica calculada con datos ingresados. "
                    "Si un estudiante supera esta brecha y tiene baja motivación y baja preparación inicial, se activa la Alerta Roja.",
                    margin_bottom="1em"
                ),
                style=style_border_box,
                min_height="150px"
            ),
            id="explicacion",
            width="100%",
            align_items="center",
            margin_bottom="4em"
        ),

        rx.divider(border_color="black"),

        # --- DOCENTE (CON INSTRUCCIONES Y VIDEO DE 10 MIN) ---
        rx.vstack(
            rx.heading("Docente - Instrucciones de Uso", size="8", font_family="serif", margin_top="1em"),
            rx.hstack(
                # LISTA DE PASOS
                rx.box(
                    rx.list.unordered(
                        rx.list.item(rx.text("Paso 1: ", font_weight="bold"), "Inicie sesión con sus credenciales."),
                        rx.list.item(rx.text("Paso 2: ", font_weight="bold"), "Lea la información en la pestaña 'Inicio'."),
                        rx.list.item(rx.text("Paso 3: ", font_weight="bold"), "Vaya a la pestaña 'Upload'."),
                        rx.list.item(rx.text("Paso 4: ", font_weight="bold"), "Cargue los archivos CSV en el orden: 1.Titulados, 2.Motivación, 3.Preparación."),
                        rx.list.item(rx.text("Paso 5: ", font_weight="bold"), "Vaya a la pestaña 'Resultados'."),
                        rx.list.item(rx.text("Paso 6: ", font_weight="bold"), "Seleccione el tipo de simulación y genere las alertas."),
                        spacing="2"
                    ),
                    style=style_border_box,
                    width="60%",
                    height="350px"
                ),

                # VIDEO YOUTUBE (URL de 10 min o menos)
                rx.vstack(
                    rx.text("Video Tutorial:", font_weight="bold", font_size="0.8em"),
                    rx.video(
                        # URL de video 10 min
                        src="https://www.youtube.com/embed/KlF33--1i8I",
                        width="100%",
                        height="auto",
                        controls=True,
                        playing=False, 
                        loop=False,
                        muted=False
                    ),
                    rx.text("(Video demostrativo)", font_size="0.7em", color="gray"),
                    width="40%"
                ),
                width="100%",
                align_items="start",
                spacing="4"
            ),
            id="docente",
            width="100%",
            margin_bottom="4em"
        ),

        rx.divider(border_color="black"),

        # --- CONTACTO ---
        rx.vstack(
            rx.heading("Contacto y Soporte", size="8", font_family="serif", margin_top="1em"),
            rx.box(
                rx.vstack(
                    rx.text("Para dudas técnicas o reporte de errores, contactar al equipo de desarrollo de Ingeniería Civil Industrial."),
                    rx.text("Repositorio del Proyecto:", font_weight="bold"),
                    rx.link(
                        "Kristhoball/estimador-riesgo: Modelo de estimador de riesgo estudiantil",
                        href="https://github.com/Kristhoball/estimador-riesgo",
                        color="blue",
                        is_external=True
                    ),
                    spacing="2"
                ),
                style=style_border_box,
                height="200px"
            ),
            id="contacto",
            width="100%",
            margin_bottom="4em"
        ),

        align_items="start", width="100%", padding="3em"
    )

def content_upload():
    return rx.vstack(
        rx.heading("Upload", size="8", font_family="serif", margin_bottom="1em"),
        rx.hstack(
            rx.box(
                rx.heading("Ingrese los datos", size="4"),
                rx.hstack(
                    rx.text("Simulado:", font_weight="bold", font_size="0.9em"),
                    rx.radio_group(["Si", "No"], direction="row", on_change=State.set_es_simulado, value=State.es_simulado),
                    rx.text(f"(Seleccionado: {State.es_simulado})", font_size="0.8em", color="blue"),
                    margin_bottom="1em", align_items="center", spacing="3"
                ),
                rx.upload(
                    rx.vstack(rx.button("Seleccionar archivos", variant="outline", size="2"), rx.text("Arrastre aquí .csv", font_size="0.8em", color="gray"), align_items="center"),
                    id="upload_box", border="1px dotted black", padding="1.5em", margin_y="1em", accept={"text/csv": [".csv"]}, multiple=True
                ),
                rx.text("Archivos en memoria:", font_weight="bold", font_size="0.9em"),
                rx.scroll_area(
                    rx.vstack(rx.cond(State.archivos_visuales, rx.foreach(State.archivos_visuales, lambda x, i: row_archivo_simple(x, i)), rx.text("Ningún archivo cargado aún.", font_style="italic", color="gray", font_size="0.8em")), width="100%"),
                    height="100px", type="always", scrollbars="vertical", bg="gray.50", padding="0.5em", border="1px solid #eee", margin_bottom="1em"
                ),
                rx.center(
                    rx.vstack(
                        rx.button("Cargar y Procesar", on_click=State.handle_upload(rx.upload_files(upload_id="upload_box")), loading=State.procesando, width="100%", color_scheme="teal"),
                        rx.cond(State.procesando, rx.vstack(rx.text(f"Procesando... {State.progreso}%", font_size="0.8em", color="teal"), rx.progress(value=State.progreso, max=100, color_scheme="teal", width="100%"), width="100%", spacing="2", align_items="center")),
                        width="100%", spacing="3"
                    ), width="100%"
                ),
                style=style_border_box, height="600px"
            ),
            rx.box(
                rx.heading("Orden Requerido:", size="4"),
                rx.text("Cargue los archivos respetando este orden:", font_size="0.9em", margin_bottom="1em", color="gray"),
                rx.list.ordered(
                    rx.list.item(rx.text("1. Titulados", font_weight="bold", color="blue")),
                    rx.list.item(rx.text("2. Cuestionario (Motivación)", font_weight="bold", color="green")),
                    rx.list.item(rx.text("3. Preparación", font_weight="bold", color="purple")),
                    spacing="3"
                ),
                rx.divider(margin_y="1.5em"),
                rx.text("Logs del sistema:", font_weight="bold", font_size="0.9em"),
                rx.scroll_area(rx.vstack(rx.foreach(State.logs, row_log), width="100%", spacing="1"), height="250px", type="always", scrollbars="vertical", bg="#f4f4f4", padding="0.5em"),
                style=style_border_box, height="600px"
            ),
            width="100%", spacing="4"
        ),
        align_items="start", width="100%", padding="3em"
    )

def content_resultados():
    return rx.vstack(
        rx.heading("Resultados", size="8", font_family="serif"),
        rx.box(
            rx.hstack(
                rx.vstack(rx.text("Generar resultados con:", font_weight="bold"), rx.scroll_area(rx.radio_group(items=State.solo_archivo_titulados, direction="column", on_change=State.seleccionar_archivo, value=State.seleccionado), height="60px"), width="50%"),
                rx.divider(orientation="vertical", height="60px", border_color="black"),
                rx.vstack(
                    rx.text("Tipo de simulación:", font_weight="bold"), 
                    rx.radio_group(["Muestra estratificada por criterio de Neyman", "Combinatoria", "Eliminación"], direction="column", on_change=State.set_tipo_simulacion, value=State.tipo_simulacion), 
                    
                    rx.cond(
                        State.tipo_simulacion == "Combinatoria",
                        rx.vstack(
                            rx.text("Máximo de Filas a Simular (por carrera):", font_size="0.8em", margin_top="0.8em"),
                            rx.input(
                                value=State.max_filas_combinatoria,
                                on_change=State.set_max_filas_combinatoria,
                                type="number",
                                placeholder="Ej: 2000",
                                max_length=5,
                            ),
                            # USAMOS LA VAR CALCULADA
                            rx.text(
                                State.info_estimacion_filas,
                                font_size="0.7em",
                                color="gray"
                            ),
                            align_items="start",
                            width="100%"
                        )
                    ),
                    
                    width="40%",
                    align_items="start"
                ),
                width="100%", spacing="4"
            ),
            rx.center(
                rx.vstack(
                    rx.button("Click para generar alerta", on_click=State.generar_graficos, loading=State.procesando_graficos, variant="outline", color_scheme="gray", width="90%", height="3em", border="1px solid black"),
                    rx.cond(State.procesando_graficos, rx.vstack(rx.text("Generando visualizaciones...", font_size="0.8em", color="blue"), rx.progress(value=State.progreso, color_scheme="blue", width="100%"), width="90%", spacing="2", align_items="center")),
                    width="100%", align_items="center", margin_top="1.5em"
                ), width="100%"
            ),
            style=style_border_box, margin_y="1.5em"
        ),
        rx.heading("Gráfica de resultado Por carrera", size="6", font_family="serif"),
        rx.box(rx.cond(State.img_carrera != "", rx.image(src=State.img_carrera, width="100%", height="auto"), rx.center(rx.text("Gráfico no generado.", color="gray", padding="2em"))), bg="white", border="1px solid black", width="100%", min_height="200px", margin_bottom="2em", overflow="hidden"),
        rx.cond(State.img_carrera != "", rx.text(f"Resultados generados con el archivo: {State.seleccionado}", font_size="0.9em", color="gray", margin_bottom="2em")),
        rx.heading("Gráfica de resultado Por estudiante", size="6", font_family="serif"),
        rx.box(rx.cond(State.img_estudiantes != "", rx.image(src=State.img_estudiantes, width="100%", height="auto"), rx.center(rx.text("Gráfico no generado o método sin gráfico.", color="gray", padding="2em"))), bg="white", border="1px solid black", width="100%", height="500px", overflow="auto"),
        rx.cond(State.img_estudiantes != "", rx.vstack(rx.text(f"Resultados generados con el archivo: {State.seleccionado}", font_size="0.9em", color="gray"), rx.text(f"Simulación visualizada: {State.tipo_simulacion}", font_size="0.9em", color="blue", font_weight="bold"), align_items="start", spacing="1", margin_bottom="3em")),
        align_items="start", width="100%", padding="3em"
    )

def content_historial():
    return rx.vstack(
        rx.heading("Historial de Simulaciones", size="4", margin_bottom="10px"),
        rx.foreach(
            State.historial,
            lambda registro, index: rx.box(
                rx.hstack(
                    rx.vstack(
                        rx.hstack(
                            rx.text(f"🕒 {registro['hora']}", font_weight="bold", font_size="sm"),
                            rx.badge(registro["tipo"], color_scheme="blue", variant="solid")
                        ),
                        rx.text(registro["detalle"], font_size="xs", color="gray"),
                        align_items="start", spacing="1"
                    ),
                    rx.spacer(), 
                    rx.icon_button(rx.icon("download"), on_click=lambda: State.descargar_simulacion(index), color_scheme="green", variant="ghost", size="2"),
                    rx.icon_button(rx.icon("trash-2"), on_click=lambda: State.eliminar_registro_historial(index), color_scheme="red", variant="ghost", size="2"),
                    width="100%", align_items="center"
                ),
                border="1px solid #e2e8f0", padding="10px", border_radius="8px", width="100%", background_color="white", shadow="sm", margin_bottom="8px"
            )
        ),
        height="100%", overflow_y="auto", padding_right="5px" 
    )

def contenido() -> rx.Component:
    
    # 1. PIEZAS
    vista_acceso_restringido = rx.center(
        rx.vstack(
            rx.heading("Acceso Restringido", size="8", color="gray"),
            rx.text("Por favor inicie sesión para ver el panel completo."),
            rx.button("Iniciar Sesión", on_click=lambda: State.set_show_login(True), size="4", color_scheme="teal", margin_top="1em"),
            spacing="4", align_items="center"
        ), height="80vh", width="100%"
    )

    contenido_dinamico = rx.cond(
        State.vista_actual == "historial",
        rx.box(content_historial(), padding="2em", width="100%"),
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
                rx.badge(f"👤 {State.usuario_actual}", color_scheme="green", variant="solid", padding="0.8em"),
                rx.button("Usuario", on_click=lambda: State.set_show_perfil(True), variant="outline", size="2", color_scheme="blue"),
                perfil_modal(), 
                rx.button("Cerrar Sesión", on_click=State.cerrar_sesion, color_scheme="red", size="2"),
                spacing="3"
            ),
            rx.box(
                rx.button("Iniciar Sesión", on_click=lambda: State.set_show_login(True), variant="outline"),
                login_modal()
            )
        ),
        width="100%", padding="1.5em", border_bottom="1px solid #e2e8f0"
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
        width="100%", height="100vh", overflow="auto", background_color="white"
    )
