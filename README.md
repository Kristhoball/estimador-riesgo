🎓 Sistema de Estimación de Riesgo Académico (MVP)

Proyecto de Ingeniería Civil Industrial - Universidad de Concepción 🇨🇱

📖 Descripción del Proyecto

Este sistema es una herramienta de analítica predictiva diseñada para apoyar la gestión docente. Su objetivo principal es detectar tempranamente a estudiantes en riesgo de deserción o retraso académico mediante el análisis de datos históricos y actuales.

El proyecto compara el rendimiento histórico de titulados anteriores con el perfil actual de los estudiantes (motivación, preparación inicial y desempeño) para generar un Semáforo de Alerta (Verde, Amarillo, Rojo).

🚀 Funcionalidades del MVP

El sistema permite a un usuario con perfil Docente:

🔐 Autenticación Segura: Sistema de login para proteger la información sensible de los estudiantes.

📂 Carga y Procesamiento de Datos:

Soporte para archivos masivos (.csv).

Validación inteligente de columnas y normalización de datos (limpieza de tildes, mayúsculas y formatos erróneos).

Procesamiento eficiente en memoria: Capaz de manejar grandes volúmenes de datos históricos sin colapsar el servidor.

🧮 Algoritmos de Simulación:

Muestra Estratificada (Criterio de Neyman): Para inferencia estadística robusta.

Combinatoria Muestreada: Para generar escenarios masivos optimizados.

Eliminación: Análisis basado estrictamente en la intersección de datos reales.

📊 Visualización de Resultados:

Gráficos interactivos generados con Matplotlib y Seaborn.

Visualización de riesgo por Carrera (visión macro).

Visualización de riesgo por Estudiante (visión micro).

⚙️ ¿Cómo funciona el Modelo?

El sistema cruza tres dimensiones críticas para calcular el riesgo ($R$):

🏛️ Titulados Anteriores (Histórico):

Analiza la duración real vs. la duración formal de la carrera.

Establece una línea base de "Latencia" ($L$) o tiempo esperado de titulación por carrera.

🧠 Motivación y Desempeño Actual:

Considera la cantidad de asignaturas reprobadas.

Evalúa el nivel de motivación declarado por el estudiante.

📚 Preparación Académica Inicial:

Utiliza el puntaje de ingreso (PAES/PSU) ponderado.

La Lógica de la Alerta

El sistema fusiona estos datos para calcular un índice de riesgo que clasifica al estudiante o carrera en:

🔴 Alerta Roja: Alto riesgo de retraso o deserción.

🟡 Alerta Amarilla: Riesgo medio, requiere seguimiento.

🟢 Alerta Verde: Trayectoria académica saludable.

🛠️ Tecnologías Utilizadas

Lenguaje: Python 3.11

Frontend & Backend: Reflex (Full-stack framework).

Ciencia de Datos: Pandas, NumPy.

Visualización: Matplotlib, Seaborn.

Despliegue: Docker, Caddy (Servidor Web), Zeabur (Cloud).

📂 Estructura de Archivos Requerida

Para el correcto funcionamiento, el sistema requiere la carga de 3 archivos CSV en el siguiente orden estricto:

Titulados.csv: Histórico de alumnos titulados (debe contener nomb_carrera, dur_total_carr, fechas, etc.).

Motivacion.csv: Encuesta actual (debe contener id_estudiante, nomb_carrera, motivacion, asignaturas_reprobadas).

Preparacion.csv: Datos de ingreso (debe contener id_estudiante, Puntaje Ponderado).

Nota: El sistema incluye validadores para asegurar que los archivos tengan las columnas correctas (ej: id_estudiante, nomb_carrera).

💻 Instalación y Ejecución Local

Clonar el repositorio:

git clone [https://github.com/tu-usuario/estimador-riesgo.git](https://github.com/tu-usuario/estimador-riesgo.git)
cd estimador-riesgo



Crear entorno virtual e instalar dependencias:

python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt



Inicializar y correr Reflex:

reflex init
reflex run



👥 Autores

Trabajo realizado por el grupo de estudiantes de Ingeniería Civil Industrial de la Universidad de Concepción.

🤖 Desarrollo Asistido

El código fuente y la construcción de la página web de este proyecto fueron desarrollados con la asistencia de herramientas de Inteligencia Artificial:

Google Gemini

ChatGPT

Este proyecto es de carácter académico.
