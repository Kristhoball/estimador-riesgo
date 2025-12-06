import csv
import re
import os
import unicodedata

# --- CONFIGURACIÓN DE TUS CÓDIGOS ---
MAPA_NOMBRES = {
    '3309': 'INGENIERIA CIVIL INDUSTRIAL', '3310': 'INGENIERIA CIVIL',
    '3303': 'INGENIERIA COMERCIAL', '3311': 'INGENIERIA CIVIL ELECTRICA',
    '3318': 'INGENIERIA CIVIL ELECTRONICA', '3319': 'INGENIERIA CIVIL INFORMATICA',
    '13072': 'INGENIERIA CIVIL INDUSTRIAL', '13069': 'INGENIERIA CIVIL',
    '13019': 'INGENIERIA COMERCIAL', '13070': 'INGENIERIA CIVIL ELECTRICA',
    '13071': 'INGENIERIA CIVIL ELECTRONICA', '13073': 'INGENIERIA CIVIL INFORMATICA'
}

def normalizar_texto(texto):
    if not isinstance(texto, str): return str(texto)
    texto = ''.join((c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn'))
    return texto.upper().strip()

CARRERAS_OBJETIVO = {
    'INGENIERIA CIVIL INDUSTRIAL', 'INGENIERIA CIVIL',
    'INGENIERIA CIVIL ELECTRICA', 'INGENIERIA CIVIL ELECTRONICA',
    'INGENIERIA COMERCIAL', 'INGENIERIA CIVIL INFORMATICA'
}
CARRERAS_OBJETIVO_NORM = {normalizar_texto(c) for c in CARRERAS_OBJETIVO}

def detectar_info_archivo(ruta_archivo):
    """Detecta encabezados y separador leyendo solo el inicio."""
    sep = ','
    try:
        with open(ruta_archivo, 'r', encoding='utf-8-sig', errors='replace') as f:
            lines = [f.readline() for _ in range(50)]
            
        for i, linea in enumerate(lines):
            linea = linea.strip()
            if not linea: continue
            
            if re.search(r'[a-zA-Z]', linea):
                if linea.count(';') > linea.count(','): sep = ';'
                else: sep = ','
                
                posibles_headers = next(csv.reader([linea], delimiter=sep))
                posibles_headers = [h.strip().replace('"', '') for h in posibles_headers]
                
                claves = ['nomb_carrera', 'Carrera que estudias actualmente', 'Código Carrera Nacional', 'Codigo Carrera Nacional']
                if any(k in posibles_headers for k in claves):
                    return i, sep, posibles_headers
    except: pass
    return 0, ',', []

def Filtrar_Archivo_En_Disco(ruta_entrada, ruta_salida, es_simulado="No"):
    """Filtra el archivo y muestra logs detallados de Aceptado/Rechazado."""
    idx_inicio, sep, headers_detectados = detectar_info_archivo(ruta_entrada)
    
    if not headers_detectados:
        raise ValueError(f"No se encontraron cabeceras válidas.")

    filas_guardadas = 0
    filas_totales = 0
    
    with open(ruta_entrada, 'r', encoding='utf-8-sig', errors='replace') as f_in, \
         open(ruta_salida, 'w', encoding='utf-8', newline='') as f_out:
        
        for _ in range(idx_inicio): next(f_in)
        
        reader = csv.reader(f_in, delimiter=sep)
        writer = csv.writer(f_out)
        
        try:
            headers = next(reader)
            headers = [h.strip().replace('"', '') for h in headers]
        except:
            raise ValueError("El archivo está vacío.")

        # --- VALIDACIÓN ID ---
        idx_id = -1
        col_id_final = "id_estudiante"
        for posible in ["id_estudiante", "id_est", "ID_ESTUDIANTE", "ID_EST", "id_alumno"]:
            if posible in headers:
                idx_id = headers.index(posible)
                break
        
        es_simulado_bool = str(es_simulado).lower() in ["si", "yes", "true", "simulado"]
        generar_id = False

        if idx_id == -1:
            if not es_simulado_bool:
                raise ValueError(f"ERROR: Seleccionaste 'No Simulado' y falta la columna 'id_estudiante'.")
            else:
                headers.append(col_id_final)
                generar_id = True
        else:
            headers[idx_id] = col_id_final

        # --- COLUMNAS ---
        idx_carrera = -1
        idx_inst = -1
        tipo_archivo = "desconocido"

        if 'nomb_carrera' in headers:
            idx_carrera = headers.index('nomb_carrera')
            if 'nomb_inst' in headers: idx_inst = headers.index('nomb_inst')
            tipo_archivo = "titulados"
        elif 'Carrera que estudias actualmente' in headers:
            idx_carrera = headers.index('Carrera que estudias actualmente')
            headers[idx_carrera] = 'nomb_carrera'
            tipo_archivo = "motivacion"
        elif 'Código Carrera Nacional' in headers or 'Codigo Carrera Nacional' in headers:
            try: idx_carrera = headers.index('Código Carrera Nacional')
            except: idx_carrera = headers.index('Codigo Carrera Nacional')
            headers[idx_carrera] = 'nomb_carrera'
            tipo_archivo = "preparacion"
        else:
            raise ValueError(f"Columnas desconocidas.")

        writer.writerow(headers)

        # --- LOOP ---
        contador_simulado = 1
        ejemplos_aceptados = 0
        
        for row in reader:
            filas_totales += 1
            if not row or len(row) <= idx_carrera: continue
            
            valor_raw = row[idx_carrera].strip()
            keep = False
            
            if tipo_archivo == "titulados":
                if idx_inst != -1 and len(row) > idx_inst:
                    inst = normalizar_texto(row[idx_inst])
                    if 'UNIVERSIDAD DE CONCEPCION' not in inst:
                        continue # No es UdeC
                
                if normalizar_texto(valor_raw) in CARRERAS_OBJETIVO_NORM:
                    keep = True

            elif tipo_archivo in ["motivacion", "preparacion"]:
                val_clean = valor_raw.split('.')[0].split(',')[0].strip()
                if val_clean in MAPA_NOMBRES:
                    row[idx_carrera] = MAPA_NOMBRES[val_clean]
                    keep = True
                elif normalizar_texto(valor_raw) in CARRERAS_OBJETIVO_NORM:
                    keep = True

            if keep:
                if generar_id:
                    if generar_id:
    # Prefijo según el tipo de archivo para que no se crucen entre sí
                        if tipo_archivo == "motivacion":
                            prefijo = "M"
                        elif tipo_archivo == "preparacion":
                            prefijo = "P"
                        elif tipo_archivo == "titulados":
                            prefijo = "T"
                        else:
                            prefijo = "X"
                        row.append(f"{prefijo}{contador_simulado}")
                        contador_simulado += 1

                writer.writerow(row)
                filas_guardadas += 1
                
                # LOG DE ÉXITO (Solo los primeros 5 para verificar)
                if ejemplos_aceptados < 5:
                    print(f"DEBUG: ✅ ACEPTADO: '{valor_raw}' -> '{row[idx_carrera]}'")
                    ejemplos_aceptados += 1
            else:
                # LOG DE RECHAZO (Solo los primeros 3 para no llenar la consola)
                if filas_totales <= 3:
                    print(f"DEBUG: ❌ IGNORADO: '{valor_raw}' (No está en la lista)")

    print(f"RESUMEN: Leídas {filas_totales} filas. Guardadas {filas_guardadas} filas con carreras válidas.")
    
    # Aviso si no guardamos nada
    if filas_guardadas == 0:
        print("ADVERTENCIA: 0 filas guardadas. Revisa si los nombres/códigos del CSV coinciden con tus filtros.")

    return filas_guardadas
