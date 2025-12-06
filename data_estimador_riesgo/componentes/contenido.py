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

# Importamos la lógica de cálculo y filtrado
# Asegúrate de que en codigo.py tengas la función Filtrar_Archivo_En_Disco que te di antes
from .codigo import Filtrar_Archivo_En_Disco 
from .codigo2 import Calcular_Resultados_Finales

# =========================================================================
# CACHE GLOBAL (Guarda rutas de archivos, no datos en RAM)
# =========================================================================
USUARIOS_CACHE = {} 
TIEMPO_EXPIRACION_MINUTOS = 30 

# --- CORRECCIÓN: Usar carpeta temporal del SISTEMA (fuera del proyecto) ---
CARPETA_SISTEMA_TEMP = tempfile.gettempdir()
CARPETA_DATOS = os.path.join(CARPETA_SISTEMA_TEMP, "datos_usuarios_riesgo")

if not os.path.exists(CARPETA_DATOS):
    try:
        os.makedirs(CARPETA_DATOS)
    except Exception as e:
        print(f"Error creando carpeta temporal: {e}")

class State(rx.State):
    usuario_cookie: str = rx.Cookie("")
    # NUEVA VARIABLE DE ESTADO PARA CONTROLAR EL LÍMITE DE SIMULACIÓN
    max_filas_combinatoria: str = "2000" # Se guarda como string para el input
    # --- VARIABLES ---
    archivos_visuales: list[str] = [] 
    
    # IMPORTANTE: Guardamos RUTAS (strings), no diccionarios
    df_rutas: list[str] = [] 
    
    seleccionado: str = ""
    logs: list[str] = ["Sistema listo. Carga: 1.Titulados, 2.Motivación, 3.Preparación."]
    
    es_simulado: str = "No"
    procesando: bool = False
    progreso: int = 0 

    historial: list[dict] = []
    tipo_simulacion: str = "Muestra estratificada por criterio de Neyman"

    # Vista por defecto
    vista_actual: str = "inicio" 

    # --- NAVEGACIÓN ---
    def ir_a_inicio(self): self.vista_actual = "inicio"
    def ir_a_upload(self): self.vista_actual = "upload"
    def ir_a_resultados(self): self.vista_actual = "resultados"
    def ir_a_historial(self): self.vista_actual = "historial"

    # Funciones para la barra (compatibilidad)
    def mostrar_panel(self): self.vista_actual = "inicio"
    def mostrar_historial(self): self.vista_actual = "historial"

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

    # --- SETTERS ---
    def set_correo_input(self, v): self.correo_input = v
    def set_pass_input(self, v): self.pass_input = v
    def set_tipo_simulacion(self, v): self.tipo_simulacion = v
    def set_es_simulado(self, v): self.es_simulado = v
    def set_show_login(self, v): self.show_login = v
    def set_show_perfil(self, v): self.show_perfil = v
    def toggle_ver_password(self): self.ver_password = not self.ver_password

    # --- SESIÓN ---
    def check_session(self):
        self.limpiar_cache_inactivos()
        if self.usuario_cookie and self.usuario_cookie in USUARIOS_CACHE:
            user_data = USUARIOS_CACHE[self.usuario_cookie]
            self.usuario_actual = self.usuario_cookie
            self.correo_input = self.usuario_cookie
            self.pass_input = user_data["pass"]
            self.historial = user_data.get("historial", [])
            self.archivos_visuales = user_data.get("archivos_visuales", [])
            
            # Recuperamos las rutas de disco
            self.df_rutas = user_data.get("df_rutas", [])
            
            self.logs = user_data.get("logs", ["Sistema listo..."])
            self.img_carrera = user_data.get("img_carrera", "")
            self.img_estudiantes = user_data.get("img_estudiantes", "")
            self.seleccionado = user_data.get("seleccionado", "")
            self.esta_logueado = True
            USUARIOS_CACHE[self.usuario_cookie]["last_active"] = time.time()
        else:
            self.esta_logueado = False
# NUEVO SETTER
    def set_max_filas_combinatoria(self, v): 
        # Aseguramos que sea un número o lo dejamos en 2000
        try:
            val = int(v)
            if val < 1: val = 1
            self.max_filas_combinatoria = str(val)
        except ValueError:
            self.max_filas_combinatoria = "2000"

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
            # Intentar borrar archivos físicos del usuario para ahorrar disco
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
            # Cargar datos existentes
            datos = USUARIOS_CACHE[email]
            self.historial = datos.get("historial", [])
            self.archivos_visuales = datos.get("archivos_visuales", [])
            self.df_rutas = datos.get("df_rutas", [])
            self.logs = datos.get("logs", ["Sesión restaurada."])
            self.img_carrera = datos.get("img_carrera", "")
            self.img_estudiantes = datos.get("img_estudiantes", "")
            self.seleccionado = datos.get("seleccionado", "")
        else:
            # Usuario Nuevo
            USUARIOS_CACHE[email] = {"pass": self.pass_input, "last_active": time.time()}
            self.historial = []
            self.archivos_visuales = []
            self.df_rutas = []
            self.logs = ["Bienvenido. Sistema listo."]
            self.img_carrera = ""
            self.img_estudiantes = ""
            self.seleccionado = ""
            
        self.usuario_actual = email
        self.usuario_cookie = email
        self.esta_logueado = True
        self.show_login = False
        self.error_login = ""
        return rx.toast.success(f"Bienvenido, {email}")

    def cerrar_sesion(self):
        self.guardar_estado_usuario()
        self.usuario_cookie = ""      
        self.usuario_actual = ""
        self.esta_logueado = False
        self.vista_actual = "inicio" # Volver al inicio
        
        # Limpieza local
        self.historial = []
        self.archivos_visuales = []
        self.df_rutas = []
        self.logs = []
        self.img_carrera = ""
        self.img_estudiantes = ""
        self.seleccionado = ""
        self.correo_input = ""
        self.pass_input = ""
        self.show_perfil = False 

    def eliminar_cuenta(self):
        if self.usuario_actual in USUARIOS_CACHE:
            # Borrar archivos físicos
            rutas = USUARIOS_CACHE[self.usuario_actual].get("df_rutas", [])
            for r in rutas:
                try: os.remove(r)
                except: pass
            del USUARIOS_CACHE[self.usuario_actual]
            
        self.cerrar_sesion()
        return rx.toast.success("Cuenta eliminada.")

    # --- ARCHIVOS ---
    @rx.var
    def solo_archivo_titulados(self) -> list[str]:
        if len(self.archivos_visuales) > 0: return [self.archivos_visuales[0]]
        return []

    def seleccionar_archivo(self, nombre: str): self.seleccionado = nombre

    def eliminar_archivo(self, nombre: str):
        if nombre in self.archivos_visuales:
            idx = self.archivos_visuales.index(nombre)
            self.archivos_visuales.pop(idx)
            
            # Borramos el archivo físico si existe y actualizamos la lista de rutas
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
            b64_carrera = registro.get("img_carrera_b64", "")
            b64_estudiantes = registro.get("img_estudiantes_b64", "")
            nombre_archivo = registro.get("archivo_origen", "desconocido")
            
            mem_zip = io.BytesIO()
            with zipfile.ZipFile(mem_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
                if b64_carrera:
                    if "," in b64_carrera: b64_carrera = b64_carrera.split(",")[1]
                    try: zf.writestr(f"grafica_carrera_{nombre_archivo}.png", base64.b64decode(b64_carrera))
                    except: pass
                if b64_estudiantes:
                    if "," in b64_estudiantes: b64_estudiantes = b64_estudiantes.split(",")[1]
                    try: zf.writestr(f"grafica_estudiantes_{nombre_archivo}.png", base64.b64decode(b64_estudiantes))
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

    # --- UPLOAD CORREGIDO QUE USA LA VARIABLE 'Simulado' ---
    async def handle_upload(self, files: list[rx.UploadFile]):
        self.procesando = True
        self.progreso = 5
        
        # DEBUG: Confirmar qué valor tiene la variable al momento de subir
        msg_inicio = f"--- Iniciando carga (Simulado: {self.es_simulado}) ---"
        print(f"DEBUG: {msg_inicio}")
        self.logs.append(msg_inicio)
        yield 

        # --- INICIALIZACIÓN DE VARIABLES DE PROGRESO ---
        num_files = len(files)
        # Distribuimos 90 puntos de progreso entre los archivos para que el último paso sea 100
        progress_increment = 90 // max(1, num_files) 
        current_progress = 5 
        # -----------------------------------------------

        for i, file in enumerate(files):
            nombre = file.filename
            if nombre not in self.archivos_visuales: self.archivos_visuales.append(nombre)
            
            tmp_in = os.path.join(CARPETA_DATOS, f"temp_in_{int(time.time())}_{i}.csv")
            tmp_out = os.path.join(CARPETA_DATOS, f"temp_out_{int(time.time())}_{i}.csv")
            
            try:
                self.logs.append(f"Recibiendo: {nombre}...")
                yield

                # Guardar
                with open(tmp_in, "wb") as buffer:
                    while True:
                        chunk = await file.read(1024*1024) 
                        if not chunk: break
                        buffer.write(chunk)
                gc.collect()

                self.logs.append(f"Validando: {nombre}...")
                yield
                
                # --- PRE-VALIDACIÓN (Para fallar rápido si no hay ID) ---
                try:
                    df_header = pd.read_csv(tmp_in, nrows=0, sep=None, engine='python')
                    cols_norm = [c.strip().lower() for c in df_header.columns]
                    
                    if self.es_simulado == "No":
                        tiene_id = "id_estudiante" in cols_norm or "id_est" in cols_norm or "id_estudiante" in df_header.columns
                        
                        if not tiene_id:
                            raise ValueError(f"ERROR: Seleccionaste 'No Simulado', pero el archivo '{nombre}' no tiene columna 'id_estudiante'.")
                
                except pd.errors.EmptyDataError:
                    raise Exception(f"El archivo '{nombre}' está vacío.")
                except ValueError as ve:
                    raise ve 
                except Exception as e:
                    print(f"Advertencia validando headers: {e}")

                # 2. Filtrar y Validar (Llamada al código externo)
                filas = Filtrar_Archivo_En_Disco(tmp_in, tmp_out, es_simulado=self.es_simulado)
                
                if filas > 0:
                    final_path = os.path.join(CARPETA_DATOS, f"{self.usuario_actual}_{int(time.time())}_{i}.csv")
                    shutil.move(tmp_out, final_path)
                    
                    if len(self.df_rutas) < len(self.archivos_visuales):
                        self.df_rutas.append(final_path)
                    else:
                        idx = self.archivos_visuales.index(nombre)
                        self.df_rutas[idx] = final_path
                    self.logs.append(f"-> OK ({filas} filas válidas).")
                else:
                    self.logs.append(f"Advertencia: '{nombre}' vacío o sin carreras de interés.")
                    
            except ValueError as ve:
                msg = str(ve)
                self.logs.append(f"RECHAZADO: {msg}")
                if nombre in self.archivos_visuales: self.eliminar_archivo(nombre)
                yield rx.window_alert(msg)
            
            except Exception as e:
                print(f"Error grave: {e}")
                self.logs.append(f"Error técnico: {str(e)[:50]}")
                if nombre in self.archivos_visuales: self.eliminar_archivo(nombre)
                yield rx.toast.error("Error al procesar archivo.", duration=3000)
            
            finally:
                if os.path.exists(tmp_in): 
                    try: os.remove(tmp_in)
                    except: pass
                if os.path.exists(tmp_out):
                     try: os.remove(tmp_out)
                     except: pass
                gc.collect()

            # --- CORRECCIÓN DE PROGRESO: Aseguramos que no pase de 99 ---
            current_progress += progress_increment
            self.progreso = min(current_progress, 99) 
            yield 

        self.guardar_estado_usuario()
        self.progreso = 100 
        self.procesando = False
        self.logs.append("--- Carga finalizada ---")
        yield rx.toast.success("Proceso completado.")

    # --- GRAFICAR LEYENDO DESDE DISCO ---
    async def generar_graficos(self):
        if len(self.df_rutas) < 3:
            yield rx.window_alert(f"Faltan archivos (tienes {len(self.df_rutas)} de 3).")
            return
        
        self.procesando_graficos = True
        yield
        import asyncio
        await asyncio.sleep(0.1)
        
        try:
            # Leer archivos pequeños ya filtrados
            df_tit = pd.read_csv(self.df_rutas[0])
            df_mot = pd.read_csv(self.df_rutas[1])
            df_prep = pd.read_csv(self.df_rutas[2])
            
            # Normalizar columnas (por si acaso codigo.py dejó nombres antiguos)
            if 'Carrera que estudias actualmente' in df_mot.columns:
                df_mot.rename(columns={'Carrera que estudias actualmente': 'nomb_carrera'}, inplace=True)
            if 'Código Carrera Nacional' in df_prep.columns:
                df_prep.rename(columns={'Código Carrera Nacional': 'nomb_carrera'}, inplace=True)

            # Calcular
            fig1, fig2 = Calcular_Resultados_Finales(df_tit, df_mot, df_prep, tipo_simulacion=self.tipo_simulacion, max_filas_simuladas=self.max_filas_combinatoria)
            
            # Guardar Imágenes
            buf = io.BytesIO(); fig1.savefig(buf, format='png', bbox_inches='tight'); buf.seek(0)
            b64_carrera_raw = base64.b64encode(buf.read()).decode('utf-8')
            self.img_carrera = f"data:image/png;base64,{b64_carrera_raw}"
            plt.close(fig1)

            b64_estudiantes_raw = ""
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
# INTERFAZ VISUAL (COMPONENTES DEFINIDOS)
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
        rx.heading("Modelo de Estimador de riesgo", size="8", font_family="serif"),
        rx.box(rx.text("Descripción general...", margin_bottom="1em"), rx.text("(Resumen)", color="red", font_weight="bold"), style=style_border_box, margin_y="2em"),
        rx.vstack(rx.heading("Index :", size="5"), rx.scroll_area(rx.vstack(rx.link("• Explicación", href="#explicacion", color="blue", text_decoration="underline"), rx.link("• Docente", href="#docente", color="blue", text_decoration="underline"), rx.link("• Contacto", href="#contacto", color="blue", text_decoration="underline"), spacing="3"), type="always", scrollbars="vertical", style={"height": "150px", "border": "1px solid black", "padding": "1em", "width": "100%"}), width="100%", max_width="400px", align_items="start", margin_bottom="4em"),
        rx.divider(border_color="black"),
        rx.vstack(rx.heading("Explicación", size="8", font_family="serif", margin_top="1em"), rx.box(rx.text("Explicación...", margin_bottom="1em"), style=style_border_box, height="300px"), id="explicacion", width="100%", align_items="center", margin_bottom="4em"),
        rx.divider(border_color="black"),
        rx.vstack(rx.heading("Docente", size="8", font_family="serif", margin_top="1em"), rx.hstack(rx.box(rx.list.unordered(rx.list.item("Paso 1..."), rx.list.item("Paso 2...")), style=style_border_box, width="60%", height="300px"), rx.vstack(rx.box(rx.center(rx.text("foto")), bg="gray.100", width="150px", height="130px"), width="40%"), width="100%"), id="docente", width="100%", margin_bottom="4em"),
        rx.divider(border_color="black"),
        rx.vstack(rx.heading("Contacto", size="8", font_family="serif", margin_top="1em"), rx.box(rx.text("Contacto..."), style=style_border_box, height="200px"), id="contacto", width="100%", margin_bottom="4em"),
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
                    margin_bottom="1em", align_items="center"
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
            # CAJA DERECHA CON LISTA COLOREADA
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
                
                # BLOQUE DE TIPO DE SIMULACIÓN
                rx.vstack(
                    rx.text("Tipo de simulación:", font_weight="bold"), 
                    rx.radio_group(["Muestra estratificada por criterio de Neyman", "Combinatoria", "Eliminación"], direction="column", on_change=State.set_tipo_simulacion, value=State.tipo_simulacion), 
                    
                    # NUEVO CAMPO DE ENTRADA CONDICIONAL
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
                            rx.text(
                                f"Simulará un máximo de {int(State.max_filas_combinatoria) * 6} filas en total (aprox).",
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

# --- ENSAMBLAJE DE VISTAS (SIN SCROLL) ---
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
