#!/usr/bin/env python3
import sys
import time


# ------------------------------------------------------------
# FUNCIONES DE LECTURA Y PREPARACIÓN DE DATOS
# ------------------------------------------------------------

def eliminar_comentario(linea: str) -> str:
    """Quita los comentarios (// ...) y espacios sobrantes."""
    return linea.split("//")[0].strip()


def leer_seccion(lineas, inicio, cantidad, parser):
    """Lee una sección del archivo con una cantidad conocida de líneas."""
    datos = []
    leidos = 0
    for i in range(inicio, len(lineas)):
        if leidos >= cantidad:
            break
        linea = eliminar_comentario(lineas[i])
        if not linea:
            continue
        try:
            datos.append(parser(linea))
            leidos += 1
        except Exception:
            print(f"Advertencia: no se pudo leer la línea -> {linea}")
    return datos


def leer_datos(nombre_archivo: str) -> dict:
    """Lee el archivo del caso y devuelve todos los datos en un diccionario."""
    try:
        with open(nombre_archivo, 'r') as f:
            lineas = f.readlines()
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo '{nombre_archivo}'")
        return None

    datos = {
        'configuracion': {},
        'nodos': {},
        'hubs': {},
        'paquetes': {},
        'aristas': {}
    }

    # --- LEER CONFIGURACIÓN GENERAL ---
    for linea in lineas:
        linea = eliminar_comentario(linea)
        if not linea:
            continue
        partes = linea.split()
        if len(partes) < 2:
            continue
        if partes[0] == "NODOS":
            datos['configuracion']['num_nodos'] = int(partes[1])
        elif partes[0] == "HUBS":
            datos['configuracion']['num_hubs'] = int(partes[1])
        elif partes[0] == "PAQUETES":
            datos['configuracion']['num_paquetes'] = int(partes[1])
        elif partes[0] == "CAPACIDAD_CAMION":
            datos['configuracion']['capacidad_camion'] = int(partes[1])
        elif partes[0] == "DEPOSITO_ID":
            datos['configuracion']['deposito_id'] = int(partes[1])
            break  # termina la lectura de configuración

    # --- DETECTAR SECCIONES (--- NODOS, HUBS, ETC.) ---
    secciones = {}
    for i, linea in enumerate(lineas):
        if "---" in linea:
            partes = linea.split("---")
            if len(partes) > 1:
                nombre = partes[1].strip().split()[0].upper()
                secciones[nombre] = i + 1

    # --- PARSERS SIMPLES PARA CADA SECCIÓN ---

    def parsear_nodo(linea):
        """Convierte una línea de la sección NODOS en una tupla (id, datos)."""
        partes = linea.split()
        id_nodo = int(partes[0])
        x = int(partes[1])
        y = int(partes[2])
        return id_nodo, {'x': x, 'y': y}


    def parsear_hub(linea):
        """Convierte una línea de la sección HUBS en una tupla (id, costo)."""
        partes = linea.split()
        id_hub = int(partes[0])
        costo = float(partes[1])
        return id_hub, costo


    def parsear_paquete(linea):
        """Convierte una línea de la sección PAQUETES en una tupla (id, {origen, destino})."""
        partes = linea.split()
        id_paquete = int(partes[0])
        origen = int(partes[1])
        destino = int(partes[2])
        return id_paquete, {'origen': origen, 'destino': destino}


    def parsear_arista(linea):
        """Convierte una línea de la sección ARISTAS en una tupla ((nodo1, nodo2), peso)."""
        partes = linea.split()
        nodo1 = int(partes[0])
        nodo2 = int(partes[1])
        peso = float(partes[2])
        return (nodo1, nodo2), peso


    # --- LEER NODOS ---
    if "NODOS" in secciones:
        nodos_list = leer_seccion(lineas, secciones["NODOS"], datos['configuracion']['num_nodos'], parsear_nodo)
        for id_nodo, props in nodos_list:
            datos['nodos'][id_nodo] = props

    # --- LEER HUBS ---
    if "HUBS" in secciones:
        hubs_list = leer_seccion(lineas, secciones["HUBS"], datos['configuracion']['num_hubs'], parsear_hub)
        for id_hub, costo in hubs_list:
            datos['hubs'][id_hub] = costo

    # --- LEER PAQUETES ---
    if "PAQUETES" in secciones:
        paquetes_list = leer_seccion(lineas, secciones["PAQUETES"], datos['configuracion']['num_paquetes'], parsear_paquete)
        for id_paq, props in paquetes_list:
            datos['paquetes'][id_paq] = props

    # --- LEER ARISTAS ---
    if "ARISTAS" in secciones:
        aristas_list = leer_seccion(lineas, secciones["ARISTAS"], float('inf'), parsear_arista)
        for edge, peso in aristas_list:
            datos['aristas'][edge] = peso
            # grafo no dirigido
            if (edge[1], edge[0]) not in datos['aristas']:
                datos['aristas'][(edge[1], edge[0])] = peso

    return datos


# ------------------------------------------------------------
# ALGORITMO DE FLOYD-WARSHALL
# ------------------------------------------------------------

def floyd_warshall(aristas, num_nodos):
    """Calcula las distancias mínimas entre todos los nodos."""
    dist = [[float('inf')] * num_nodos for _ in range(num_nodos)]
    for i in range(num_nodos):
        dist[i][i] = 0
    for (u, v), peso in aristas.items():
        dist[u][v] = peso
        dist[v][u] = peso

    for k in range(num_nodos):
        for i in range(num_nodos):
            for j in range(num_nodos):
                if dist[i][k] + dist[k][j] < dist[i][j]:
                    dist[i][j] = dist[i][k] + dist[k][j]
    return dist


# ------------------------------------------------------------
# BÚSQUEDA DE RUTA Y HUBS (VERSIÓN SIMPLE Y CLARA)
# ------------------------------------------------------------

def calcular_mejor_camino(datos, matriz):
    """Decide qué hubs activar y calcula una ruta razonable con menor costo."""

    deposito = datos['configuracion']['deposito_id']
    capacidad = datos['configuracion']['capacidad_camion']
    hubs = list(datos['hubs'].keys())
    costo_hubs = datos['hubs']

    # Agrupar cuántos paquetes van a cada destino
    paquetes_por_destino = {}
    for _, paquete in datos['paquetes'].items():
        destino = paquete['destino']
        paquetes_por_destino[destino] = paquetes_por_destino.get(destino, 0) + 1

    # Valores iniciales
    mejor_costo = float('inf')
    mejor_hubs = []
    mejor_ruta = []
    mejor_distancia = 0

    # Recorremos todas las combinaciones posibles de hubs activados (simple)
    for i in range(2 ** len(hubs)):
        hubs_activos = []
        costo_activacion = 0

        for j, hub in enumerate(hubs):
            if (i >> j) & 1:  # si el bit está encendido, el hub se activa
                hubs_activos.append(hub)
                costo_activacion += costo_hubs[hub]

        # Armar los viajes del camión
        destinos = list(paquetes_por_destino.keys())
        viajes = []
        viaje_actual = []
        carga_actual = 0

        # dividir los destinos en grupos que respeten la capacidad del camión
        for d in destinos:
            cant = paquetes_por_destino[d]
            if carga_actual + cant > capacidad:
                viajes.append(viaje_actual)
                viaje_actual = []
                carga_actual = 0
            viaje_actual.append(d)
            carga_actual += cant
        if viaje_actual:
            viajes.append(viaje_actual)

        # Calcular distancia total de todos los viajes
        distancia_total = 0
        ruta_total = [deposito]

        for viaje in viajes:
            mejor_inicio = deposito
            menor_distancia_viaje = float('inf')

            # probar comenzar desde el depósito o desde algún hub activo
            for punto_inicio in [deposito] + hubs_activos:
                distancia_viaje = matriz[punto_inicio][viaje[0]]
                for k in range(len(viaje) - 1):
                    distancia_viaje += matriz[viaje[k]][viaje[k + 1]]
                distancia_viaje += matriz[viaje[-1]][deposito]
                if distancia_viaje < menor_distancia_viaje:
                    menor_distancia_viaje = distancia_viaje
                    mejor_inicio = punto_inicio

            distancia_total += menor_distancia_viaje
            ruta_total.append(mejor_inicio)
            for d in viaje:
                ruta_total.append(d)
            ruta_total.append(deposito)

        costo_total = distancia_total + costo_activacion

        if costo_total < mejor_costo:
            mejor_costo = costo_total
            mejor_hubs = hubs_activos
            mejor_ruta = ruta_total
            mejor_distancia = distancia_total

    costo_solo_hubs = mejor_costo - mejor_distancia

    return mejor_ruta, mejor_hubs, mejor_costo, mejor_distancia, costo_solo_hubs


# ------------------------------------------------------------
# PROGRAMA PRINCIPAL
# ------------------------------------------------------------

def main():
    if len(sys.argv) != 2:
        print(f"Uso: {sys.argv[0]} <archivo_caso.txt>")
        sys.exit(1)

    archivo = sys.argv[1]
    inicio = time.time()

    datos = leer_datos(archivo)
    if datos is None:
        print("No se pudo leer el archivo correctamente.")
        sys.exit(1)

    num_nodos = datos['configuracion']['num_nodos']
    matriz = floyd_warshall(datos['aristas'], num_nodos)

    ruta, hubs, costo_total, distancia, costo_hubs = calcular_mejor_camino(datos, matriz)

    fin = time.time()
    duracion = fin - inicio

    # --- GUARDAR RESULTADO ---
    with open("solucion.txt", "w") as f:
        f.write("// --- HUBS ACTIVADOS ---\n")
        for h in hubs:
            f.write(f"{h}\n")
        f.write("\n// --- RUTA OPTIMA ---\n")
        f.write(" -> ".join(map(str, ruta)) + "\n")
        f.write("\n// --- METRICAS ---\n")
        f.write(f"COSTO_TOTAL: {costo_total:.2f}\n")
        f.write(f"DISTANCIA_RECORRIDA: {distancia:.2f}\n")
        f.write(f"COSTO_HUBS: {costo_hubs:.2f}\n")
        f.write(f"TIEMPO_EJECUCION: {duracion:.6f} segundos\n")

    print("Archivo solucion.txt generado con éxito.")


if __name__ == "__main__":
    main()