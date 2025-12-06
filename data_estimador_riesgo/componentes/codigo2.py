import pandas as pd
import seaborn as sns
import matplotlib
# IMPORTANTE: Configurar backend no interactivo para evitar bloqueos en web
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import numpy as np
import math
import gc # Garbage Collector para liberar memoria

# Configuramos un estado aleatorio global para la reproducibilidad
np.random.seed(42)
RANDOM_STATE = 42

# =================================================================
# FUNCIONES AUXILIARES
# =================================================================

def Filtrar_Titulados(df):
    df_filtrado = df[['nomb_carrera', 'anio_ing_carr_ori', 'sem_ing_carr_ori', 'anio_ing_carr_act', 'sem_ing_carr_act', 'dur_total_carr', 'fecha_obtencion_titulo']].copy()
    
    df_filtrado['anio_ing_carr_ori'] = df_filtrado['anio_ing_carr_ori'].replace([9995,9998,9999,1900], np.nan)
    df_filtrado['anio_ing_carr_act'] = df_filtrado['anio_ing_carr_act'].replace([9998,9999], np.nan)
    sem_a_fraccion = {1: 0, 2: 0.5}
    df_filtrado['sem_ing_carr_ori'] = df_filtrado['sem_ing_carr_ori'].replace([0], np.nan).map(sem_a_fraccion) 
    df_filtrado['sem_ing_carr_act'] = df_filtrado['sem_ing_carr_act'].replace([0], np.nan).map(sem_a_fraccion)

    df_filtrado['año_exacto_ingreso'] = np.where(df_filtrado['anio_ing_carr_act'].notna(), df_filtrado['anio_ing_carr_act'] + df_filtrado['sem_ing_carr_act'].fillna(0), df_filtrado['anio_ing_carr_ori'] + df_filtrado['sem_ing_carr_ori'].fillna(0))

    df_filtrado['fecha_obtencion_titulo'] = pd.to_datetime(df_filtrado['fecha_obtencion_titulo'].dropna().astype(int).astype(str),format='%Y%m%d', errors='coerce')
    df_filtrado['año_obtencion_titulo'] = df_filtrado['fecha_obtencion_titulo'].dt.year
    df_filtrado['dia_obtencion_titulo'] = df_filtrado['fecha_obtencion_titulo'].dt.day
    df_filtrado['año_exacto_titulo'] = df_filtrado['año_obtencion_titulo'] + df_filtrado['dia_obtencion_titulo'] / 365

    df_filtrado = df_filtrado[['nomb_carrera', 'año_exacto_ingreso', 'año_exacto_titulo', 'dur_total_carr']]
    return df_filtrado

def Filtrar_Motivacion(df):
    df_filtrado= df[[ 'id_estudiante','nomb_carrera', 'Indica la cantidad de asignaturas reprobadas desde su inicio de la carrera hasta la fecha. Si no has reprobado, marca 0' , 'Indica tu nivel actual de motivación por estudiar tu carrera']].copy()
    return df_filtrado

def Filtrar_Preparacion(df):
    df_filtrado = df[['id_estudiante','nomb_carrera', 'Puntaje Ponderado']].copy()
    return df_filtrado

def Alerta_Titulados(df_filtrado):
    df_filtrado = df_filtrado.copy()
    df_filtrado['duracion_real'] = df_filtrado['año_exacto_titulo'] - df_filtrado['año_exacto_ingreso']
    df_filtrado['duracion_formal'] = df_filtrado['dur_total_carr']
    df_filtrado = df_filtrado[['nomb_carrera', 'duracion_real', 'duracion_formal']]
    
    carreras_titulacion = df_filtrado['nomb_carrera'].unique()
    resultados_tit = []
    for i in carreras_titulacion:
        df_carrera_tit = df_filtrado[df_filtrado['nomb_carrera'] == i]
        duracion_real_i = df_carrera_tit['duracion_real'].mean()
        duracion_formal_i = df_carrera_tit['duracion_formal'].mean()
        resultados_tit.append({'nomb_carrera': i, 'duracion_real i': duracion_real_i, 'duracion_formal i': duracion_formal_i})
    
    df_res = pd.DataFrame(resultados_tit)
    df_res['B_i_años'] = df_res['duracion_real i'] - df_res['duracion_formal i'] / 2
    df_res['B_i'] = df_res['B_i_años'] * 2
    return df_res[['nomb_carrera', 'B_i']]

def Alerta_Motivacion(df_filtrado, r):
    df_filtrado = df_filtrado.copy()
    df_filtrado.columns = ['id_estudiante', 'nomb_carrera', 'r_j', 'P_j']
    a=1 
    df_filtrado['r_j'] = a * df_filtrado['r_j']
    df_filtrado_normalizado = df_filtrado.copy()
    df_filtrado_normalizado['P_j'] = 1 - (df_filtrado['P_j'].astype(float) / 5)
    
    if r == 'estudiante':
        return df_filtrado_normalizado
    elif r == 'carrera':
        carreras_motivacion = df_filtrado_normalizado['nomb_carrera'].unique()
        resultados_mot = []
        for i in carreras_motivacion:
            df_carrera_mot = df_filtrado_normalizado[df_filtrado_normalizado['nomb_carrera'] == i]
            AP_i = df_carrera_mot['r_j'].mean()
            P_i = df_carrera_mot['P_j'].mean()
            resultados_mot.append({'nomb_carrera': i, 'AP_i': AP_i, 'P_i': P_i})
        return pd.DataFrame(resultados_mot)

def Alerta_Preparacion(df_filtrado, r):
    df_filtrado = df_filtrado.copy()
    df_filtrado.columns = ['id_estudiante', 'nomb_carrera', 'PA_j']
    df_filtrado_normalizado = df_filtrado.copy()
    df_filtrado_normalizado['PA_j'] = 1- (df_filtrado['PA_j'].astype(float) / 850.0)
 
    if r == 'estudiante':
        return df_filtrado_normalizado
    elif r == 'carrera':
        carreras_preparacion = df_filtrado_normalizado['nomb_carrera'].unique()
        resultados_pre = []
        for i in carreras_preparacion:
              df_carrera_pre = df_filtrado_normalizado[df_filtrado_normalizado['nomb_carrera'] == i]
              IPA_i = df_carrera_pre['PA_j'].mean()
              resultados_pre.append({'nomb_carrera': i, 'IPA_i': IPA_i})
        return pd.DataFrame(resultados_pre)

def Neyman_2poblaciones(df_Motivacion, df_Preparacion, carrera='nomb_carrera',
                        variable_mot='P_j', variable_prep='PA_j',
                        error=0.01, z=1.96):

    filas = []
    for c in df_Motivacion[carrera].unique():
        gm = df_Motivacion[df_Motivacion[carrera] == c]
        gp = df_Preparacion[df_Preparacion[carrera] == c]

        if gm.empty or gp.empty:
            continue

        N_comb = min(len(gm), len(gp))

        # Calcular SD robusto
        S_m = gm[variable_mot].std(ddof=1)
        S_p = gp[variable_prep].std(ddof=1)
        S_comb = np.nanmean([S_m, S_p])

        if np.isnan(S_comb) or S_comb == 0:
            S_comb = 1.0  # valor mínimo para no caer en n = 0

        filas.append([c, N_comb, S_comb])

    if not filas:
        return 10, {}  # mínimo de seguridad

    dfN = pd.DataFrame(filas, columns=['carrera', 'N_comb', 'S_comb'])
    Nh = dfN.set_index('carrera')['N_comb']
    Sh = dfN.set_index('carrera')['S_comb']

    N = Nh.sum()
    sum_ShNh = (Sh * Nh).sum()
    sum_Sh2Nh = (Sh**2 * Nh).sum()

    numerador = (z**2) * (sum_ShNh**2)
    D = (error**2) / (z**2)
    denominador = (N**2 * D) + sum_Sh2Nh

    if denominador == 0:
        denominador = 1

    n = numerador / denominador
    n = max(10, min(int(n), int(N)))  # nunca permitir n = 0

    nh = (n * Nh * Sh / sum_ShNh).round().astype(int)
    
    # Asegurar que ninguna carrera quede con nh = 0
    nh[nh == 0] = 1

    # Ajustar suma
    diferencia = n - nh.sum()
    if diferencia != 0:
        nh.iloc[-1] += diferencia

    return n, nh.to_dict()


def Ejemplo_neyman(df_solo_mot, df_solo_pre, nh_dicc):
    bloque = []
    
    # Lista de variables que necesitamos de las fuentes
    vars_mot = ['nomb_carrera', 'r_j', 'P_j'] 
    vars_prep = ['nomb_carrera', 'PA_j'] 
    
    for carr, nh in nh_dicc.items():
        if nh <= 0: continue
        
        gm = df_solo_mot[df_solo_mot['nomb_carrera'] == carr].reset_index(drop=True)
        gp = df_solo_pre[df_solo_pre['nomb_carrera'] == carr].reset_index(drop=True)
        
        if gm.empty or gp.empty: continue
        
        # Muestreo seguro
        replace_m = len(gm) < nh
        replace_p = len(gp) < nh

        try:
            # Seleccionamos solo las variables necesarias para el muestreo
            m = gm[vars_mot].sample(n=nh, replace=replace_m, random_state=RANDOM_STATE).reset_index(drop=True)
            g = gp[vars_prep].sample(n=nh, replace=replace_p, random_state=RANDOM_STATE).reset_index(drop=True)
        except ValueError as e:
             print(f"Advertencia de muestreo para {carr}: {e}")
             continue
             
        # Concatenación para formar la simulación
        g['nomb_carrera'] = carr
        
        m.index = range(len(m))
        g.index = range(len(g))
        
        simulacion = pd.concat([m.add_suffix('_mot'), g.add_suffix('_prep')], axis=1)
        simulacion['nomb_carrera'] = carr
        simulacion['fuente'] = 'simulacion_neyman'
        bloque.append(simulacion)
    
    bloques = pd.concat(bloque, ignore_index=True) if bloque else pd.DataFrame()
    
    # Renombramos y limpiamos columnas para que coincidan con df_real
    if not bloques.empty:
        bloques = bloques.rename(columns={
            'P_j_mot': 'P_j',
            'PA_j_prep': 'PA_j',
            'r_j_mot': 'r_j'
        })
        
        # Eliminamos sufijos sobrantes (nomb_carrera_mot/prep y columnas de datos duplicadas)
        bloques = bloques.drop(columns=[
            'nomb_carrera_mot', 
            'nomb_carrera_prep', 
            'P_j_prep', 
            'PA_j_mot', 
            'r_j_prep' 
        ], errors='ignore')
        
        # Creamos 'id_simulado' y reordenamos
        bloques['id_simulado'] = range(1,len(bloques)+1)
        
    # Devolvemos el DataFrame con el ID de simulación
    return bloques[['id_simulado', 'nomb_carrera','r_j', 'P_j', 'PA_j', 'fuente']]

def etiquetar_alerta_desde_prob(R):
    if R > 0.03: return "Roja"
    if -0.03 <= R <= 0.03: return "Amarilla"
    return "Verde"

def Alerta_Estudiantes(df, df_Titulados_car, permitir_incompletos=False):
    df_final_est = df.copy()
    
    # 1. Normalización de ID (si viene de Ejemplo_neyman)
    if 'id_simulado' in df_final_est.columns:
        df_final_est = df_final_est.rename(columns={'id_simulado': 'id_estudiante'})
    
    # 2. Aseguramos las columnas de datos
    required_cols = ['id_estudiante', 'nomb_carrera', 'r_j', 'P_j', 'PA_j','fuente']
    for col in required_cols:
        if col not in df_final_est.columns:
            if col in ['r_j', 'P_j', 'PA_j']:
                df_final_est[col] = np.nan
            else:
                raise ValueError(f"Error en Alerta_Estudiantes: Falta la columna clave '{col}'. Columnas: {df_final_est.columns.tolist()}")

    # 3. Tipos numéricos
    df_final_est['r_j'] = df_final_est['r_j'].astype(float)
    df_final_est['P_j'] = df_final_est['P_j'].astype(float)
    df_final_est['PA_j'] = df_final_est['PA_j'].astype(float)

    # ❗ Manejo de faltantes
    if not permitir_incompletos:
        # Para Neyman / Combinatoria: solo casos con las 3 variables
        df_final_est = df_final_est.dropna(subset=['r_j','P_j','PA_j'], how='any')
        if df_final_est.empty:
            # devolver DF vacío con columnas esperadas
            return pd.DataFrame(columns=['id_estudiante','fuente','nomb_carrera',
                                         'S_j','L_j','P_j','PA_j','R_j','Alerta'])
    else:
        # Para Eliminación: rellenar faltantes con 0
        df_final_est[['r_j','P_j','PA_j']] = df_final_est[['r_j','P_j','PA_j']].fillna(0)

    a = 1
    df_final_est['S_j'] = a * df_final_est['r_j']
    
    # 4. Merge con datos de Titulados
    df_final_est = df_final_est.merge(df_Titulados_car[['nomb_carrera', 'B_i']], on='nomb_carrera', how='left')
    
    df_final_est['L_j'] = df_final_est['B_i'].fillna(0)
    alpha = 0.6
    beta = 0.4
    
    # 5. Cálculo final del riesgo (R_j)
    df_final_est['R_j'] = alpha * (df_final_est['S_j'] - df_final_est['L_j']) + \
                          beta * (df_final_est['P_j'] + df_final_est['PA_j'])
    
    if "Alerta" not in df_final_est.columns:
        df_final_est["Alerta"] = df_final_est["R_j"].apply(etiquetar_alerta_desde_prob)
        
    return df_final_est[['id_estudiante','fuente','nomb_carrera','S_j','L_j','P_j','PA_j','R_j','Alerta']]

def Alerta_Carrera(df):
    alpha = 0.6
    beta = 0.4
    df_completo_carr = df.copy()
    df_completo_carr['R_i'] = alpha *(df_completo_carr['AP_i'] - df_completo_carr['B_i']) + beta* (df_completo_carr['P_i'] + df_completo_carr['IPA_i'] ) 
    
    if "Alerta" not in df_completo_carr.columns:
        df_completo_carr["Alerta"] = df_completo_carr["R_i"].apply(etiquetar_alerta_desde_prob)
    return df_completo_carr

# --- FUNCIONES DE GRÁFICOS PARA WEB (Sin cambios) ---

def Grafico_Estudiantes_Web(df):
    alerta_palette = {"Verde": "#2ca02c", "Amarilla": "#fffb00", "Roja": "#ff0000"}
    orden_alertas = ["Roja", "Amarilla", "Verde"]
    carreras = df['nomb_carrera'].unique()
    
    filas = math.ceil(len(carreras) / 2)
    if filas == 0 or df.empty:
        fig = plt.figure()
        plt.text(0.5, 0.5, "No hay datos para graficar", ha='center')
        return fig

    fig, axes = plt.subplots(filas, 2, figsize=(12, 4 * filas))
    if filas == 1 and len(carreras) <= 2: axes = np.array([axes])
    axes = axes.flatten()

    for i, carrera_nombre in enumerate(carreras):
        if i < len(axes):
            ax = axes[i]
            data_carrera = df[df['nomb_carrera'] == carrera_nombre]
            if not data_carrera.empty:
                sns.histplot(
                    data=data_carrera, x='R_j', bins=18, hue='Alerta',
                    multiple="stack", palette=alerta_palette, hue_order=orden_alertas, ax=ax
                )
            ax.set_title(f'R_j: {carrera_nombre}', fontsize=10)
            ax.set_xlabel('')
    
    for j in range(i + 1, len(axes)):
        axes[j].axis('off')

    plt.tight_layout()
    return fig 

def Grafico_Carrera_Web(df):
    alerta_palette = {"Verde": "#2ca02c", "Amarilla": "#fffb00", "Roja": "#ff0000"}
    
    fig = plt.figure(figsize=(10, 6))
    if not df.empty:
        g = sns.barplot(
            data=df, x='nomb_carrera', y='R_i', hue='Alerta',
            palette=alerta_palette, dodge=False
        )
        plt.title("Riesgo promedio por carrera", fontsize=16)
        plt.xticks(rotation=45, ha='right')
    else:
        plt.text(0.5, 0.5, "No hay datos para graficar", ha='center')
        
    plt.tight_layout()
    return fig

# =================================================================
# FUNCIÓN MAESTRA CON LOS 3 MÉTODOS
# =================================================================

def Calcular_Resultados_Finales(df_tit, df_mot, df_prep, tipo_simulacion="Muestra estratificada por criterio de Neyman", max_filas_simuladas=2000):
    
    # 1. PREPARACIÓN
    df_Titulados = Filtrar_Titulados(df_tit)
    df_Motivacion = Filtrar_Motivacion(df_mot)
    df_Preparacion = Filtrar_Preparacion(df_prep)

    df_Titulados_car = Alerta_Titulados(df_Titulados)

    df_Motivacion_car = Alerta_Motivacion(df_Motivacion, 'carrera')
    df_Motivacion_est = Alerta_Motivacion(df_Motivacion, 'estudiante')

    df_Preparacion_car = Alerta_Preparacion(df_Preparacion, 'carrera')
    df_Preparacion_est = Alerta_Preparacion(df_Preparacion, 'estudiante')  

    # 2. GRÁFICO CARRERA (Siempre se genera)
    df_merge = pd.merge(df_Titulados_car, df_Motivacion_car, on='nomb_carrera')
    df_final_carr = pd.merge(df_merge, df_Preparacion_car, on='nomb_carrera')
    df_final_carr = Alerta_Carrera(df_final_carr)
    fig_carrera = Grafico_Carrera_Web(df_final_carr)
    fig_estudiantes = None

    # 3. PREPARACIÓN DE CONJUNTOS (Estudiantes)
    ids_mot = set(df_Motivacion_est['id_estudiante'])
    ids_pre = set(df_Preparacion_est['id_estudiante'])
    ids_comunes = ids_mot.intersection(ids_pre)
    ids_solo_mot = ids_mot - ids_comunes
    ids_solo_pre = ids_pre - ids_comunes

    df_solo_mot = df_Motivacion_est[df_Motivacion_est['id_estudiante'].isin(ids_solo_mot)].copy()
    df_solo_pre = df_Preparacion_est[df_Preparacion_est['id_estudiante'].isin(ids_solo_pre)].copy()
    
    # Rellenar con NaN las columnas faltantes para que la concatenación sea segura
    df_solo_mot['PA_j'] = np.nan
    df_solo_mot['fuente'] = 'solo_mot'
    
    df_solo_pre['r_j'] = np.nan
    df_solo_pre['P_j'] = np.nan
    df_solo_pre['fuente'] = 'solo_prep'

    # Intersección real (df_real)
    df_real = df_Motivacion_est[df_Motivacion_est['id_estudiante'].isin(ids_comunes)].merge(
        df_Preparacion_est[df_Preparacion_est['id_estudiante'].isin(ids_comunes)], 
        on=['id_estudiante', 'nomb_carrera'], how='inner'
    )
    df_real['fuente'] = 'no_simulado'

    # --- SELECCIÓN DEL ALGORITMO ---
    
    if tipo_simulacion == "Muestra estratificada por criterio de Neyman":
        # === NEYMAN ===
        n, nh = Neyman_2poblaciones(df_solo_mot, df_solo_pre, carrera='nomb_carrera', variable_mot='P_j', variable_prep='PA_j', error=0.01, z=1.96)
        
        if n > 0 and nh:
            df_simulacion_neyman = Ejemplo_neyman(df_solo_mot, df_solo_pre, nh)
        else:
            df_simulacion_neyman = pd.DataFrame()
            
        # Unir reales + simulados
        if not df_real.empty:
            df_real['id_estudiante'] = df_real['id_estudiante'].astype(str)
            max_id_real = pd.to_numeric(df_real['id_estudiante'], errors='coerce').max()
            if pd.isna(max_id_real): max_id_real = 0
        else:
            max_id_real = 0

        # Renombrar id_simulado a id_estudiante
        df_simulacion_neyman.rename(columns={'id_simulado': 'id_estudiante'}, inplace=True)
        # Ajuste de IDs para simulación
        if not df_simulacion_neyman.empty:
            df_simulacion_neyman['id_estudiante'] = [str(i) for i in range(int(max_id_real)+1, int(max_id_real)+1 + len(df_simulacion_neyman))]
        
        # FIX: Concatenar REALES + SIMULADOS
        df_final_est = pd.concat([df_real, df_simulacion_neyman], ignore_index=True)
        
        df_final_est = Alerta_Estudiantes(df_final_est, df_Titulados_car)
        fig_estudiantes = Grafico_Estudiantes_Web(df_final_est)

# Dentro de la función Calcular_Resultados_Finales:

# Dentro de la función Calcular_Resultados_Finales:

# Dentro de la función Calcular_Resultados_Finales:

    elif tipo_simulacion == "Combinatoria":
        # ===========================================================
        # COMBINATORIA LIGERA PARA WEB: Procesamiento por carrera
        # ===========================================================
        carrera_pesada = 'INGENIERIA COMERCIAL'
        carreras = df_Motivacion_est['nomb_carrera'].unique()

        # Quitamos id_estudiante para no confundir con simulados
        df_mot_est_combinatoria = df_Motivacion_est.drop(columns=['id_estudiante'], errors='ignore')
        df_prep_est_combinatoria = df_Preparacion_est.drop(columns=['id_estudiante'], errors='ignore')

        # Filtrar carreras “livianas”
        df_mot_light = df_mot_est_combinatoria[df_mot_est_combinatoria['nomb_carrera'] != carrera_pesada]
        df_prep_light = df_prep_est_combinatoria[df_prep_est_combinatoria['nomb_carrera'] != carrera_pesada]
        df_tit_light = df_Titulados[df_Titulados['nomb_carrera'] != carrera_pesada].copy()

        df_tit_light['duracion_real'] = df_tit_light['año_exacto_titulo'] - df_tit_light['año_exacto_ingreso']
        df_tit_light['duracion_formal'] = df_tit_light['dur_total_carr']
        df_tit_light = df_tit_light[['nomb_carrera', 'duracion_real', 'duracion_formal']]

        # Lista de carreras a graficar
        lista_carreras_graficar = list(df_tit_light['nomb_carrera'].unique())
        if carrera_pesada in carreras:
            lista_carreras_graficar.append(carrera_pesada)

        if not lista_carreras_graficar:
            fig_estudiantes = plt.figure()
            plt.text(0.5, 0.5, "Sin datos para Combinatoria", ha='center')
            return fig_carrera, fig_estudiantes

        filas = max(1, math.ceil(len(lista_carreras_graficar) / 2))
        fig_estudiantes, axes = plt.subplots(filas, 2, figsize=(12, 4 * filas), squeeze=False)
        axes = axes.flatten()

        alerta_palette = {"Verde": "#2ca02c", "Amarilla": "#fffb00", "Roja": "#ff0000"}
        orden_alertas = ["Roja", "Amarilla", "Verde"]

        # Límite de filas a simular por carrera (Tu límite propuesto)
        MAX_FILAS_CARRERA = int(max_filas_simuladas)

        # --- BUCLE PRINCIPAL DE PROCESAMIENTO (POR CARRERA) ---
        for i, carr in enumerate(lista_carreras_graficar):
            ax = axes[i] if i < len(axes) else None
            if ax is None:
                break
                
            # Inicializamos df_to_plot por si el if/else falla
            df_to_plot = pd.DataFrame() 

            if carr == carrera_pesada:
                # Tratamiento para INGENIERIA COMERCIAL (Usando df_Titulados original)
                df_t_sub = df_Titulados[df_Titulados['nomb_carrera'] == carrera_pesada].copy()
                df_m_sub = df_mot_est_combinatoria[df_mot_est_combinatoria['nomb_carrera'] == carrera_pesada]
                df_p_sub = df_prep_est_combinatoria[df_prep_est_combinatoria['nomb_carrera'] == carrera_pesada]

                df_t_sub['duracion_real'] = df_t_sub['año_exacto_titulo'] - df_t_sub['año_exacto_ingreso']
                df_t_sub['duracion_formal'] = df_t_sub['dur_total_carr']
                df_t_sub = df_t_sub[['nomb_carrera', 'duracion_real', 'duracion_formal']]
            else:
                # Tratamiento para carreras "livianas" (Usando df_tit_light)
                df_t_sub = df_tit_light[df_tit_light['nomb_carrera'] == carr].copy()
                df_m_sub = df_mot_light[df_mot_light['nomb_carrera'] == carr].copy()
                df_p_sub = df_prep_light[df_prep_light['nomb_carrera'] == carr].copy()
            
            # --- LÓGICA DE MUESTREO Y CRUCE (Unificada) ---
            if not df_t_sub.empty and not df_m_sub.empty and not df_p_sub.empty:
                sample_n = min(MAX_FILAS_CARRERA, len(df_t_sub), len(df_m_sub), len(df_p_sub))

                if sample_n > 0:
                    # FIX: Asegurar que el muestreo use el RANDOM_STATE
                    tit_sample = df_t_sub.sample(n=sample_n, replace=(len(df_t_sub) < sample_n),
                                                 random_state=RANDOM_STATE).reset_index(drop=True)
                    mot_sample = df_m_sub.sample(n=sample_n, replace=(len(df_m_sub) < sample_n),
                                                 random_state=RANDOM_STATE).reset_index(drop=True)
                    prep_sample = df_p_sub.sample(n=sample_n, replace=(len(df_p_sub) < sample_n),
                                                 random_state=RANDOM_STATE).reset_index(drop=True)

                    # Unión Paralela (No Producto Cruzado gigante)
                    df_to_plot = pd.concat(
                        [tit_sample,
                         mot_sample.drop(columns=['nomb_carrera']),
                         prep_sample.drop(columns=['nomb_carrera'])],
                        axis=1
                    )
                    df_to_plot['nomb_carrera'] = carr
                    df_to_plot['fuente'] = 'combinatoria'
                    # Aseguramos ID como string para consistencia con df_real
                    df_to_plot['id_estudiante'] = [str(x) for x in range(1, len(df_to_plot) + 1)]
                
            # --- GRAFICAR Y LIMPIAR ---
            if not df_to_plot.empty:
                df_alerta_carr = Alerta_Estudiantes(df_to_plot, df_Titulados_car)
                sns.histplot(
                    data=df_alerta_carr, x='R_j', bins=20, hue='Alerta',
                    multiple="stack", palette=alerta_palette, hue_order=orden_alertas, ax=ax
                )
                ax.ticklabel_format(style='sci', axis='y', scilimits=(0, 0))
                del df_alerta_carr
            else:
                ax.text(0.5, 0.5, "Sin datos", ha='center')

            ax.set_title(f'R_j: {carr}', fontsize=10)
            ax.set_xlabel('')
            
            # Limpiar DataFrames temporales para esta carrera
            del df_t_sub, df_m_sub, df_p_sub, df_to_plot 
            gc.collect()

        # Apagar ejes sobrantes
        for j in range(i + 1, len(axes)):
            axes[j].axis('off')

        plt.tight_layout()
        
    return fig_carrera, fig_estudiantes

    elif tipo_simulacion == "Eliminación":
    # === ELIMINACIÓN: usar TODOS los estudiantes sin simulación ===
    # - df_real: tienen motivación y preparación
    # - df_solo_mot: solo motivación
    # - df_solo_pre: solo preparación
    
        df_elim_completo = pd.concat(
            [df_real, df_solo_mot, df_solo_pre],
            ignore_index=True
        )

        if not df_elim_completo.empty:
        # Aquí permitimos incompletos (rellena NaN con 0 dentro de la función)
            df_final_elim = Alerta_Estudiantes(df_elim_completo.copy(), df_Titulados_car,
                                           permitir_incompletos=True)
            fig_estudiantes = Grafico_Estudiantes_Web(df_final_elim)
        else:
            fig_estudiantes = plt.figure()
            plt.text(0.5, 0.5, "No hay datos para el análisis por Eliminación", ha='center')
    return fig_carrera, fig_estudiantes
