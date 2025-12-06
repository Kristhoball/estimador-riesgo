import csv
import os
import re

# --- CONFIGURACIÓN DE FILTROS ---
CARRERAS_OBJETIVO = {
    'INGENIERIA CIVIL INDUSTRIAL', 'INGENIERIA CIVIL',
    'INGENIERIA CIVIL ELECTRICA', 'INGENIERIA CIVIL ELECTRONICA',
    'INGENIERIA COMERCIAL', 'INGENIERIA CIVIL INFORMATICA'
}

CODIGOS_OBJETIVO = {
    '3309.0', '3310.0', '3303.0', '3311.0', '3318.0', '3319.0',
    '13072.0', '13069.0', '13019.0', '13070.0', '13071.0', '13073.0',
    '3309', '3310', '3303', '3311', '3318', '3319',
    '13072', '13069', '13019', '13070', '13071', '13073'
}

MAPA_NOMBRES = {
    '3309.0': 'INGENIERIA CIVIL INDUSTRIAL', '3310.0': 'INGENIERIA CIVIL',
    '3303.0': 'INGENIERIA COMERCIAL', '3311.0': 'INGENIERIA CIVIL ELECTRICA',
    '3318.0': 'INGENIERIA CIVIL ELECTRONICA', '3319.0': 'INGENIERIA CIVIL INFORMATICA',
    '13072.0': 'INGENIERIA CIVIL INDUSTRIAL', '13069.0': 'INGENIERIA CIVIL',
    '13019.0': 'INGENIERIA COMERCIAL', '13070.0': 'INGENIERIA CIVIL ELECTRICA',
    '13071.0': 'INGENIERIA CIVIL ELECTRONICA', '13073.0': 'INGENIERIA CIVIL INFORMATICA'
}

def detectar_formato_seguro(ruta_archivo):
    sep = ','
    header_idx = 0
    try:
        with open(ruta_archivo, 'r', encoding='utf-8', errors='replace') as f:
            for i in range(50):
                linea = f.readline()
                if not linea: break
                # Si encontramos letras, asumimos que es el header
                if re.search(r'[a-zA-Z]', linea):
                    header_idx = i
                    if linea.count(';') > linea.count(','):
                        sep = ';'
                    return header_idx, sep
    except: pass
    return 0, ','

def Filtrar_Archivo_En_Disco(ruta_entrada, ruta_salida):
    idx, sep = detectar_formato_seguro(ruta_entrada)
    
    filas_guardadas = 0
    
    with open(ruta_entrada, 'r', encoding='utf-8', errors='replace') as f_in, \
         open(ruta_salida, 'w', encoding='utf-8', newline='') as f_out:
        
        # Saltar líneas basura
        for _ in range(idx): next(f_in)
        
        reader = csv.reader(f_in, delimiter=sep)
        writer = csv.writer(f_out)
        
        try:
            headers = next(reader)
        except StopIteration:
            return 0 # Archivo vacío

        # Normalizar headers
        headers = [h.strip() for h in headers]
        writer.writerow(headers) # Escribir encabezados en el archivo nuevo
        
        # Identificar columnas clave
        idx_carrera = -1
        idx_inst = -1
        tipo = "otro"
        
        if 'nomb_carrera' in headers:
            idx_carrera = headers.index('nomb_carrera')
            if 'nomb_inst' in headers: idx_inst = headers.index('nomb_inst')
            tipo = "titulados"
        elif 'Carrera que estudias actualmente' in headers:
            idx_carrera = headers.index('Carrera que estudias actualmente')
            tipo = "motivacion"
        elif 'Código Carrera Nacional' in headers:
            idx_carrera = headers.index('Código Carrera Nacional')
            tipo = "preparacion"
            
        if idx_carrera == -1: return 0 # No se puede filtrar

        # BUCLE LÍNEA POR LÍNEA (Eficiencia Pura)
        for row in reader:
            if not row or len(row) <= idx_carrera: continue
            
            valor = row[idx_carrera].strip()
            keep = False
            
            if tipo == "titulados":
                # Filtro Institución
                if idx_inst != -1 and len(row) > idx_inst:
                    if row[idx_inst].strip() != 'UNIVERSIDAD DE CONCEPCION':
                        continue
                # Filtro Carrera
                if valor in CARRERAS_OBJETIVO:
                    keep = True
            
            elif tipo in ["motivacion", "preparacion"]:
                # Limpiar código (quitar .0)
                val_clean = valor.replace('.0', '')
                # Si el código es uno de los nuestros, guardamos
                if val_clean in CODIGOS_OBJETIVO or valor in CODIGOS_OBJETIVO:
                    # TRUCO: Reemplazamos el código por el nombre aquí mismo para ahorrar trabajo luego
                    if val_clean in MAPA_NOMBRES:
                        row[idx_carrera] = MAPA_NOMBRES[val_clean]
                    elif valor in MAPA_NOMBRES:
                        row[idx_carrera] = MAPA_NOMBRES[valor]
                    
                    # Renombrar columna headers si fuera necesario (lo hacemos al leer con pandas luego)
                    keep = True
            
            if keep:
                writer.writerow(row)
                filas_guardadas += 1
                
    return filas_guardadas

# Mantenemos alias vacíos para no romper importaciones viejas
def Datos_Normalizados(a): pass
def Restricciones(a, b): pass
